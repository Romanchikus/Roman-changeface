import {
  ALL_FORMATS,
  BlobSource,
  BufferTarget,
  Conversion,
  Input,
  Mp4OutputFormat,
  Output,
} from "mediabunny";

export async function trimVideo(file: File, start: number, end: number): Promise<File> {
  const input = new Input({ source: new BlobSource(file), formats: ALL_FORMATS });
  const target = new BufferTarget();
  const output = new Output({ format: new Mp4OutputFormat(), target });
  const conversion = await Conversion.init({ input, output, trim: { start, end } });
  if (!conversion.isValid) {
    const reason = conversion.discardedTracks[0]?.reason ?? "unsupported";
    throw new Error(`Could not cut this video (${reason}).`);
  }
  await conversion.execute();
  const buffer = target.buffer;
  if (!buffer) throw new Error("Could not cut this video.");
  const base = file.name.replace(/\.[^.]+$/, "") || "clip";
  return new File([buffer], `${base}.mp4`, { type: "video/mp4" });
}
