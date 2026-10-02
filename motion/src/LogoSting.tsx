import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { COLOR, DUR, EASE, STAGGER } from "./tokens";
import type { LogoStingLayer } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// 예고(선이 그어짐) → 선을 따라 로고가 드러남 → 정착. 로고는 균일 배율과 가림만 쓰고 비율·색은 그대로 둔다
export const LogoSting: React.FC<{ layer: LogoStingLayer }> = ({ layer }) => {
  const frame = useCurrentFrame() - (layer.start ?? 0);
  const w = layer.width;
  const line = interpolate(frame, [0, DUR.medium], [0, 1], { ...clamp, easing: EASE.move });
  const reveal = interpolate(frame, [DUR.medium - 2, DUR.medium + DUR.long], [0, 1], { ...clamp, easing: EASE.enter });
  const lineOut = interpolate(frame, [DUR.medium + DUR.long - 4, DUR.medium + DUR.long + 6], [1, 0], clamp);
  const scale = 1.04 - 0.04 * reveal;
  const tagStart = DUR.medium + DUR.long;
  const words = (layer.tagline ?? "").split(" ").filter(Boolean);
  if (frame < 0) return null;
  return (
    <div style={{ position: "absolute", left: layer.x - w / 2, top: layer.y, width: w, transform: "translateY(-50%)" }}>
      <div style={{ transform: `scale(${scale})`, clipPath: `inset(0 ${(1 - reveal) * 100}% 0 0)` }}>
        <Img src={staticFile(layer.src)} style={{ width: w, height: "auto", display: "block" }} />
      </div>
      {/* 예고 선: 왼쪽에서 그어지고, 드러남의 앞 가장자리를 따라간 뒤 사라진다 */}
      <div style={{ position: "absolute", left: reveal > 0 ? w * reveal : 0, top: "50%", width: reveal > 0 ? 4 : w * 0.18 * line, height: reveal > 0 ? "100%" : 4,
        transform: "translateY(-50%)", background: layer.accent ?? COLOR.accent, opacity: lineOut, borderRadius: 2 }} />
      {words.length > 0 && (
        <div style={{ display: "flex", justifyContent: "center", flexWrap: "wrap", columnGap: w * 0.02, marginTop: w * 0.06,
          fontFamily: "GmarketSansMedium", fontSize: w * 0.075, color: layer.taglineColor ?? "white" }}>
          {words.map((wd, i) => {
            const p = interpolate(frame - tagStart - i * STAGGER.word, [0, DUR.medium], [0, 1], { ...clamp, easing: EASE.enter });
            return <span key={i} style={{ display: "inline-block", opacity: p, transform: `translateY(${(1 - p) * w * 0.03}px)` }}>{wd}</span>;
          })}
        </div>
      )}
    </div>
  );
};
