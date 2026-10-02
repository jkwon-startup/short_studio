import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLOR, EASE, SPRING, STAGGER } from "./tokens";
import type { AppScreenLayer } from "./types";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// t가 null이면 "없음", 음수면 "이미 완료"
const since = (frame: number, t: number | null | undefined) => (t === null || t === undefined ? -Infinity : frame - t);

export const AppScreen: React.FC<{ layer: AppScreenLayer }> = ({ layer }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { x, y, w, h } = layer.box;
  const acc = layer.accent ?? COLOR.accent;
  const pad = w * 0.06;
  const r = Math.max(10, w * 0.025);

  const tIn = since(frame, layer.inputAt);
  const tType = since(frame, layer.typeAt);
  const tSend = since(frame, layer.sendAt);
  const tBuild = since(frame, layer.buildAt);
  const tMis = since(frame, layer.misalignAt);
  const tRe = since(frame, layer.realignAt);
  const built = tBuild >= 0;

  // 입력창: 아래에서 올라오며 정착
  const inP = tIn === -Infinity ? 0 : interpolate(tIn, [0, 10], [0, 1], { ...clamp, easing: EASE.enter });
  const sendP = tSend === -Infinity ? 0 : interpolate(tSend, [0, 6], [0, 1], { ...clamp, easing: EASE.enter });
  const inputFade = built ? interpolate(tBuild, [0, 6], [1, 0], clamp) : 1;
  const lines = layer.typeLines ?? 3;
  const ib = { x: x + pad, y: y + h - pad - h * 0.22, w: w - pad * 2, h: h * 0.22 };

  // 블록 조립: 헤더 → 히어로 → 카드 2 → 버튼, 그룹 시차
  const block = (i: number) => {
    if (!built) return { o: 0, dy: 0, s: 1 };
    const p = spring({ frame: tBuild - i * STAGGER.group, fps, config: SPRING.ui, durationInFrames: 12 });
    return { o: p, dy: (1 - p) * h * 0.08, s: 0.94 + 0.06 * p };
  };

  // 버튼: 어긋남(짧은 흔들림) → 스프링으로 복귀
  const bw = w * 0.36, bh = h * 0.12, bx = x + (w - bw) / 2, by = y + h * 0.8;
  let btnDx = 0, btnDy = 0, btnRot = 0, btnColor = acc;
  if (tMis >= 0) {
    const jump = interpolate(tMis, [0, 4], [0, 1], { ...clamp, easing: EASE.enter });
    const shake = tMis < 9 ? Math.sin(tMis * 2.2) * 6 * (1 - tMis / 9) : 0;
    btnDx = w * 0.08 * jump + shake; btnDy = -h * 0.14 * jump; btnRot = -6 * jump; btnColor = COLOR.danger;
  }
  if (tRe >= 0) {
    const back = spring({ frame: tRe, fps, config: SPRING.settle });
    btnDx = interpolate(back, [0, 1], [btnDx, 0]); btnDy = interpolate(back, [0, 1], [btnDy, 0]);
    btnRot = interpolate(back, [0, 1], [btnRot, 0]); btnColor = back > 0.5 ? acc : COLOR.danger;
  }
  const ring = tRe >= 0 ? interpolate(tRe, [8, 26], [0, 1], { ...clamp, easing: EASE.enter }) : 0;
  const check = tRe >= 0 ? spring({ frame: tRe - 12, fps, config: SPRING.snap }) : 0;
  const b = [0, 1, 2, 3, 4].map(block);

  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%" }}>
      {/* 화면 바탕 */}
      <div style={{ position: "absolute", left: x, top: y, width: w, height: h, background: built ? COLOR.surface : "transparent", opacity: built ? b[0].o : 1, borderRadius: 4 }} />
      {/* 입력 단계 */}
      {inputFade > 0 && tIn !== -Infinity && (
        <div style={{ opacity: inputFade }}>
          {Array.from({ length: lines }).map((_, i) => {
            const p = tType === -Infinity ? 0 : interpolate(tType - i * STAGGER.line * 3, [0, 10], [0, 1], { ...clamp, easing: EASE.move });
            return <div key={i} style={{ position: "absolute", left: x + pad, top: y + pad + i * h * 0.13, height: h * 0.07, width: (w - pad * 2 - i * 70) * p, background: COLOR.line, borderRadius: 999 }} />;
          })}
          <div style={{ position: "absolute", left: ib.x, top: ib.y + (1 - inP) * 40, width: ib.w, height: ib.h, opacity: inP, background: "white", border: `3px solid #C9D3D2`, borderRadius: ib.h / 2, boxShadow: "0 8px 24px rgba(0,0,0,.12)" }}>
            {tType === -Infinity && <div style={{ position: "absolute", left: 28, top: ib.h * 0.25, width: 5, height: ib.h * 0.5, background: acc, opacity: Math.floor(frame / 8) % 2 ? 1 : 0.15 }} />}
            <div style={{ position: "absolute", right: ib.h * 0.18, top: ib.h * 0.15, width: ib.h * 0.7, height: ib.h * 0.7, borderRadius: "50%", background: tType >= 0 ? acc : "#9FB3B1", transform: `scale(${1 + 0.18 * Math.sin(Math.PI * sendP)})` }} />
          </div>
        </div>
      )}
      {/* 조립 블록 */}
      {built && (
        <>
          <div style={{ position: "absolute", left: x, top: y + b[0].dy, width: w, height: h * 0.14, background: acc, opacity: b[0].o }} />
          <div style={{ position: "absolute", left: x + pad, top: y + h * 0.2 + b[1].dy, width: w - pad * 2, height: h * 0.28, background: COLOR.accentSoft, borderRadius: r, opacity: b[1].o, transform: `scale(${b[1].s})` }} />
          <div style={{ position: "absolute", left: x + pad, top: y + h * 0.53 + b[2].dy, width: w / 2 - pad * 1.5, height: h * 0.21, background: COLOR.card, borderRadius: r, opacity: b[2].o, transform: `scale(${b[2].s})` }} />
          <div style={{ position: "absolute", left: x + w / 2 + pad / 2, top: y + h * 0.53 + b[3].dy, width: w / 2 - pad * 1.5, height: h * 0.21, background: COLOR.card, borderRadius: r, opacity: b[3].o, transform: `scale(${b[3].s})` }} />
          {/* 링 펄스 */}
          {ring > 0 && ring < 1 && (
            <div style={{ position: "absolute", left: bx - bw * 0.3 * ring, top: by - bh * 0.6 * ring, width: bw * (1 + 0.6 * ring), height: bh * (1 + 1.2 * ring), borderRadius: bh, border: `4px solid ${COLOR.ok}`, opacity: 1 - ring }} />
          )}
          <div style={{ position: "absolute", left: bx, top: by + b[4].dy, width: bw, height: bh, background: btnColor, borderRadius: bh / 2, opacity: b[4].o,
            transform: `translate(${btnDx}px, ${btnDy}px) rotate(${btnRot}deg) scale(${b[4].s})`, boxShadow: "0 6px 16px rgba(0,0,0,.18)" }} />
          {check > 0.01 && (
            <div style={{ position: "absolute", left: bx + bw + 14, top: by - 4, width: bh + 8, height: bh + 8, borderRadius: "50%", background: COLOR.ok, transform: `scale(${check})`, display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontSize: bh * 0.7, fontWeight: 700 }}>✓</div>
          )}
        </>
      )}
    </div>
  );
};
