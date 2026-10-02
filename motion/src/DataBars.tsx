import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { COLOR, DUR, EASE, STAGGER } from "./tokens";
import type { DataBarsLayer } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
// 막대가 쓸 수 있는 길이 비율. scripts/claude_adapters/autopilot.py의 DATA_TRACK과 같은 값
const TRACK = { vertical: 0.56, horizontal: 0.58 };

const decimals = (v: number) => (String(v).split(".")[1] ?? "").length;

// 막대 길이는 값에 비례(0 기준 선형)하고, 숫자는 막대와 같은 진행도로 올라가 끝에서 원래 값과 정확히 같아진다. 오버슈트 없음
export const DataBars: React.FC<{ layer: DataBarsLayer }> = ({ layer }) => {
  const frame = useCurrentFrame() - (layer.start ?? 0);
  const { x, y, w, h } = layer.box;
  const hz = layer.orientation === "horizontal";
  const n = layer.items.length;
  const top = layer.mapping?.max ?? layer.max ?? Math.max(...layer.items.map((i) => i.value));
  const track = layer.mapping?.track_px ?? (hz ? w * TRACK.horizontal : h * TRACK.vertical);
  const text = layer.color ?? "white";
  const dp = Math.max(...layer.items.map((i) => decimals(i.value)));
  const titleP = interpolate(frame, [0, DUR.medium], [0, 1], { ...clamp, easing: EASE.enter });
  const base = DUR.short; // 제목이 자리 잡은 뒤 막대 시작
  const grow = (i: number) => interpolate(frame - base - i * STAGGER.group, [0, DUR.long], [0, 1], { ...clamp, easing: EASE.move });
  const fs = hz ? Math.min(h / n * 0.3, w * 0.05) : Math.min(w / n * 0.2, h * 0.055);
  const titleH = h * 0.14, footH = h * 0.07;
  const sourceP = interpolate(frame - base - n * STAGGER.group - DUR.long, [0, DUR.medium], [0, 1], clamp);
  const fill = (hl?: boolean) => (hl ? layer.highlightColor ?? "#7FE0D2" : layer.barColor ?? "rgba(255,255,255,.38)");
  const num = (v: number, p: number) => `${(v * p).toFixed(dp)}${layer.unit}`;
  if (frame < 0) return null;

  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, color: text, fontFamily: "GmarketSansMedium" }}>
      {layer.title && (
        <div style={{ position: "absolute", left: 0, top: 0, width: w, fontFamily: "GmarketSansBold", fontSize: Math.min(titleH * 0.55, w * 0.07), lineHeight: 1.2,
          opacity: titleP, transform: `translateY(${(1 - titleP) * 16}px)` }}>{layer.title}</div>
      )}
      {hz ? (
        layer.items.map((it, i) => {
          const p = grow(i), rowH = (h - titleH - footH) / n, labelW = w - track - w * 0.16;
          return (
            <div key={i} style={{ position: "absolute", left: 0, top: titleH + i * rowH, width: w, height: rowH, display: "flex", alignItems: "center", fontSize: fs }}>
              <div style={{ width: labelW, paddingRight: w * 0.02, textAlign: "right", opacity: Math.min(1, p * 3) }}>{it.label}</div>
              <div style={{ width: (track * it.value / top) * p, height: rowH * 0.46, background: fill(it.highlight), borderRadius: 6 }} />
              <div style={{ marginLeft: w * 0.02, fontFamily: "GmarketSansBold", opacity: Math.min(1, p * 3) }}>{num(it.value, p)}</div>
            </div>
          );
        })
      ) : (
        <>
          {layer.items.map((it, i) => {
            const p = grow(i), colW = w / n, bh = (track * it.value / top) * p, baseY = h - footH - fs * 1.9;
            return (
              <React.Fragment key={i}>
                <div style={{ position: "absolute", left: i * colW, top: baseY - bh - fs * 1.5, width: colW, textAlign: "center", fontFamily: "GmarketSansBold", fontSize: fs * 1.15, opacity: Math.min(1, p * 3) }}>{num(it.value, p)}</div>
                <div style={{ position: "absolute", left: i * colW + colW * 0.22, top: baseY - bh, width: colW * 0.56, height: bh, background: fill(it.highlight), borderRadius: "8px 8px 0 0" }} />
                <div style={{ position: "absolute", left: i * colW, top: baseY + fs * 0.5, width: colW, textAlign: "center", fontSize: fs, opacity: Math.min(1, p * 3) }}>{it.label}</div>
              </React.Fragment>
            );
          })}
          {/* 0 기준선 */}
          <div style={{ position: "absolute", left: 0, top: h - footH - fs * 1.9, width: w * titleP, height: 3, background: text, opacity: 0.55 }} />
        </>
      )}
      <div style={{ position: "absolute", left: 0, bottom: 0, width: w, fontSize: Math.max(28, w * 0.034), fontFamily: "GmarketSansLight", opacity: 0.8 * sourceP, color: text }}>출처: {layer.source}</div>
    </div>
  );
};
