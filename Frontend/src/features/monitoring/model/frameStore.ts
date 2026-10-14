import type { Frame, Snapshot } from "./types";
export function createFrameStore() {
  let frames: Snapshot["frames"] = {};
  const listeners = new Map<Frame["scene"], Set<() => void>>();
  const notify = (scene: Frame["scene"]) =>
    listeners.get(scene)?.forEach((listener) => listener());
  return {
    get: (scene: Frame["scene"]) => frames[scene],
    subscribe: (scene: Frame["scene"], listener: () => void) => {
      if (!listeners.has(scene)) listeners.set(scene, new Set());
      listeners.get(scene)!.add(listener);
      return () => {
        listeners.get(scene)?.delete(listener);
      };
    },
    replace: (value: Snapshot["frames"]) => {
      frames = { ...value };
      notify("arrival");
      notify("boarding");
    },
    update: (frame: Frame) => {
      frames[frame.scene] = frame;
      notify(frame.scene);
    },
  };
}
export type FrameStore = ReturnType<typeof createFrameStore>;
