import type { VolumePoint } from "./types";

const BUCKET_MINUTES = 5;

function addMinutes(clock: string, minutes: number) {
  const [hours, mins] = clock.split(":").map(Number);
  const total = (hours * 60 + mins + minutes) % (24 * 60);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

export function timeWindow(volume: VolumePoint[]) {
  if (volume.length === 0) return "";
  const last = volume[volume.length - 1].start;
  return `${volume[0].start} to ${addMinutes(last, BUCKET_MINUTES)} UTC`;
}
