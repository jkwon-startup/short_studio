import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { AppScreen } from "./AppScreen";
import { DataBars } from "./DataBars";
import { KineticFull } from "./KineticFull";
import { KineticText } from "./KineticText";
import { LogoSting } from "./LogoSting";
import { COLOR, EASE, SPRING } from "./tokens";
import type { Camera, NotifyLayer, SceneProps } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const useCamera = (cam: Camera | undefined, duration: number) => {
  const frame = useCurrentFrame();
  if (!cam) return { transform: "none", origin: "50% 50%" };
  const s = cam.start ?? 0, e = cam.end ?? duration;
  const p = interpolate(frame, [s, Math.max(s + 1, e)], [0, 1], { ...clamp, easing: cam.ease === "enter" ? EASE.enter : EASE.move });
  const f = { scale: 1, x: 0, y: 0, ...cam.from }, t = { scale: 1, x: 0, y: 0, ...cam.to };
  const sc = f.scale + (t.scale - f.scale) * p, x = f.x + (t.x - f.x) * p, y = f.y + (t.y - f.y) * p;
  const o = cam.origin ? `${cam.origin.x}px ${cam.origin.y}px` : "50% 50%";
  return { transform: `translate(${x}px, ${y}px) scale(${sc})`, origin: o };
};

const Notify: React.FC<{ layer: NotifyLayer }> = ({ layer }) => {
  const frame = useCurrentFrame() - (layer.start ?? 0);
  const { fps } = useVideoConfig();
  const p = spring({ frame, fps, config: SPRING.snap });
  const acc = layer.accent ?? COLOR.accent;
  return (
    <div style={{ position: "absolute", left: layer.x, top: layer.y, width: 480, height: 140, borderRadius: 36, background: "rgba(255,255,255,.94)",
      boxShadow: "0 18px 40px rgba(0,0,0,.25)", transform: `translateX(${(1 - p) * 120}px) scale(${0.9 + 0.1 * p})`, opacity: Math.min(1, p * 1.4) }}>
      <div style={{ position: "absolute", left: 30, top: 30, width: 80, height: 80, borderRadius: "50%", background: acc }} />
      <div style={{ position: "absolute", left: 130, top: 40, width: 310 * Math.min(1, p * 1.2), height: 30, borderRadius: 12, background: "#CBD5D4" }} />
      <div style={{ position: "absolute", left: 130, top: 85, width: 220 * Math.min(1, p * 1.1), height: 25, borderRadius: 12, background: "#E1E7E6" }} />
    </div>
  );
};

export const Scene: React.FC<SceneProps> = (props) => {
  const cam = useCamera(props.camera, props.durationInFrames);
  const bg = props.background ?? { type: "transparent" };
  return (
    <AbsoluteFill style={{ background: bg.type === "color" ? bg.value : "transparent", overflow: "hidden" }}>
      {/* 무대: 배경과 화면 UI를 함께 움직여 UI가 화면에 붙어 따라간다 */}
      <AbsoluteFill style={{ transform: cam.transform, transformOrigin: cam.origin }}>
        {bg.type === "image" && <Img src={staticFile(bg.src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />}
        {props.layers.filter((l) => l.type === "app_screen").map((l, i) => <AppScreen key={i} layer={l as any} />)}
      </AbsoluteFill>
      {/* 카메라와 무관한 화면 위 레이어 */}
      {props.layers.map((l, i) => {
        switch (l.type) {
          case "kinetic_text": return <KineticText key={i} layer={l} />;
          case "notify_card": return <Notify key={i} layer={l} />;
          case "logo_sting": return <LogoSting key={i} layer={l} />;
          case "data_bars": return <DataBars key={i} layer={l} />;
          case "kinetic_full": return <KineticFull key={i} layer={l} />;
          default: return null;
        }
      })}
    </AbsoluteFill>
  );
};
