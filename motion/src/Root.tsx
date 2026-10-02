import React from "react";
import { Composition, staticFile } from "remotion";
import { loadFont } from "@remotion/fonts";
import { Scene } from "./Scene";
import type { SceneProps } from "./types";

// Gmarket Sans(OFL): 렌더 시 public-dir/fonts/ 에 복사된 파일을 쓴다
for (const w of ["Bold", "Medium", "Light"]) {
  loadFont({ family: `GmarketSans${w}`, url: staticFile(`fonts/GmarketSansTTF${w}.ttf`) }).catch(() => undefined);
}

const defaults: SceneProps = { width: 1080, height: 1920, fps: 30, durationInFrames: 60, background: { type: "color", value: "#101414" }, layers: [] };

export const Root: React.FC = () => (
  <Composition
    id="Scene"
    component={Scene as any}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={60}
    defaultProps={defaults}
    calculateMetadata={({ props }) => ({
      width: (props as SceneProps).width, height: (props as SceneProps).height,
      fps: (props as SceneProps).fps, durationInFrames: (props as SceneProps).durationInFrames,
    })}
  />
);
