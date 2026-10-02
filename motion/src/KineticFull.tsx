import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { DUR, EASE, STAGGER } from "./tokens";
import type { KineticFullLayer } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// 글자 폭 어림(em): 한글·한자 1, 공백 0.3, 그 밖 0.6
const em = (s: string) => [...s].reduce((a, c) => a + (c === " " ? 0.3 : c.charCodeAt(0) > 0x2e80 ? 1 : 0.6), 0);

// 구(의미 단위)가 화면을 채운다. 단어가 가림막 아래에서 올라와 정착하고, 머무는 동안 천천히 커지다가 다음 구가 오면 위로 밀려 나간다
export const KineticFull: React.FC<{ layer: KineticFullLayer }> = ({ layer }) => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();
  const cy = layer.y ?? height / 2;
  return (
    <>
      {layer.phrases.map((ph, k) => {
        const end = layer.phrases[k + 1]?.at ?? durationInFrames + DUR.short;
        if (frame < ph.at || frame >= end) return null;
        const t = frame - ph.at;
        const lines = ph.text.split("\n");
        const size = Math.min(layer.maxSize ?? width * 0.2, (width * 0.86) / Math.max(...lines.map(em)), (height * 0.5) / (lines.length * 1.2));
        const out = interpolate(frame, [end - DUR.short, end], [0, 1], { ...clamp, easing: EASE.exit });
        const drift = 1 + 0.035 * (t / Math.max(1, end - ph.at));
        const hl = new Set(ph.highlight ?? []);
        let wi = 0;
        return (
          <div key={k} style={{ position: "absolute", left: 0, top: cy, width, transform: `translateY(-50%) translateY(${-out * size * 0.6}px) scale(${drift})`, opacity: 1 - out,
            fontFamily: "GmarketSansBold", fontSize: size, lineHeight: 1.2, color: layer.color ?? "white", textAlign: "center" }}>
            {lines.map((ln, li) => (
              <div key={li} style={{ display: "flex", justifyContent: "center", columnGap: size * 0.3 }}>
                {ln.split(" ").filter(Boolean).map((wd) => {
                  const p = interpolate(t - wi++ * STAGGER.word, [0, DUR.medium], [0, 1], { ...clamp, easing: EASE.enter });
                  return (
                    <span key={wi} style={{ display: "inline-block", overflow: "hidden", paddingBottom: size * 0.1 }}>
                      <span style={{ display: "inline-block", transform: `translateY(${(1 - p) * size * 1.15}px)`, color: hl.has(wd) ? layer.highlightColor ?? "#7FE0D2" : undefined }}>{wd}</span>
                    </span>
                  );
                })}
              </div>
            ))}
          </div>
        );
      })}
    </>
  );
};
