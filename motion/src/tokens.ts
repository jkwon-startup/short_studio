import { Easing } from "remotion";

// 스튜디오 모션 토큰 (docs/motion-design-standard.md 기준값을 30fps 프레임으로 양자화)
export const EASE = {
  enter: Easing.bezier(0.16, 1, 0.3, 1), // 정착(등장)
  move: Easing.bezier(0.65, 0, 0.35, 1), // 연결(화면 내 이동·카메라)
  exit: Easing.bezier(0.7, 0, 0.84, 0), // 퇴장
};

export const DUR = { short: 5, medium: 10, long: 20 }; // 0.17s / 0.33s / 0.67s
export const STAGGER = { word: 2, line: 4, group: 5 };

export const SPRING = {
  ui: { damping: 200 }, // 오버슈트 없음
  snap: { damping: 18, stiffness: 180 }, // 강조, 약한 튕김(8% 이하)
  settle: { damping: 14, stiffness: 140 },
};

export const COLOR = {
  accent: "#0B4F4A",
  accentSoft: "#CFE3E0",
  surface: "#F7FAF9",
  card: "#E4ECEB",
  line: "#D7DDDC",
  danger: "#D93A3A",
  ok: "#2E9E6B",
  ink: "#1A1A1A",
};
