import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { EASE, STAGGER } from "./tokens";
import type { KineticTextLayer } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// 단어 단위 등장. 핵심어만 색 하나로 강조(굵기·크기·색 중 하나만 바꾼다)
export const KineticText: React.FC<{ layer: KineticTextLayer }> = ({ layer }) => {
  const frame = useCurrentFrame() - (layer.start ?? 0);
  const size = layer.size ?? 72;
  const words = layer.text.split(" ");
  const hl = new Set(layer.highlight ?? []);
  return (
    <div style={{ position: "absolute", left: layer.x - (layer.maxWidth ?? 900) / 2, top: layer.y, width: layer.maxWidth ?? 900,
      display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: size * 0.28, rowGap: size * 0.18,
      fontFamily: `GmarketSans${layer.weight ?? "Bold"}`, fontSize: size, lineHeight: 1.15, color: layer.color ?? "white" }}>
      {words.map((wd, i) => {
        const t = frame - i * STAGGER.word;
        const p = interpolate(t, [0, 12], [0, 1], { ...clamp, easing: EASE.enter });
        const mask = layer.mode === "mask_up";
        return (
          <span key={i} style={{ display: "inline-block", overflow: mask ? "hidden" : "visible", paddingBottom: mask ? size * 0.12 : 0 }}>
            <span style={{ display: "inline-block", transform: `translateY(${(1 - p) * (mask ? size * 1.1 : size * 0.45)}px)`, opacity: mask ? 1 : p,
              color: hl.has(wd) ? layer.highlightColor ?? "#7FE0D2" : undefined, textShadow: "0 3px 14px rgba(0,0,0,.45)" }}>{wd}</span>
          </span>
        );
      })}
    </div>
  );
};
