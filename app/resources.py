import asyncio
from dataclasses import dataclass

_CPU: tuple[int, int] | None = None
_cpu_lock = asyncio.Lock()


@dataclass(frozen=True, slots=True)
class MachineSample:
    cpu_percent: float | None
    ram_used_bytes: int
    ram_total_bytes: int
    vram_used_bytes: int | None
    vram_total_bytes: int | None
    gpu_util_percent: float | None


async def sample_machine() -> MachineSample:
    ram, gpu = await asyncio.gather(asyncio.to_thread(_memory), _gpu())
    ram_total, ram_used = ram
    vram_used, vram_total, gpu_util = gpu
    return MachineSample(await _cpu_percent(), ram_used, ram_total, vram_used, vram_total, gpu_util)


async def _cpu_percent() -> float | None:
    global _CPU
    async with _cpu_lock:
        idle, total = await asyncio.to_thread(_cpu_times)
        previous = _CPU
        _CPU = (idle, total)
    if previous is None:
        return None
    delta = total - previous[1]
    if delta <= 0:
        return None
    busy = 100 * (1 - (idle - previous[0]) / delta)
    return round(max(0.0, min(100.0, busy)), 1)


def _cpu_times() -> tuple[int, int]:
    with open("/proc/stat", encoding="ascii") as handle:
        parts = handle.readline().split()
    numbers = [int(part) for part in parts[1:]]
    idle = numbers[3] + (numbers[4] if len(numbers) > 4 else 0)
    return idle, sum(numbers)


def _memory() -> tuple[int, int]:
    info: dict[str, int] = {}
    with open("/proc/meminfo", encoding="ascii") as handle:
        for line in handle:
            key, raw = line.split(":", 1)
            info[key] = int(raw.strip().split()[0]) * 1024
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", 0)
    return total, max(0, total - available)


async def _gpu() -> tuple[int | None, int | None, float | None]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError:
        return None, None, None
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return None, None, None
    if proc.returncode != 0 or not stdout:
        return None, None, None
    used, total, util = stdout.decode().strip().splitlines()[0].split(",")
    mib = 1024 * 1024
    return int(used) * mib, int(total) * mib, float(util)
