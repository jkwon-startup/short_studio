export type Box = { x: number; y: number; w: number; h: number };

export type Camera = {
  // 무대(배경+UI) 전체를 움직인다. origin은 1080x1920 무대 좌표
  from?: { scale?: number; x?: number; y?: number };
  to?: { scale?: number; x?: number; y?: number };
  start?: number; // 프레임
  end?: number;
  origin?: { x: number; y: number };
  ease?: "enter" | "move";
};

export type AppScreenLayer = {
  type: "app_screen";
  box: Box;
  accent?: string;
  // 시점(프레임). 음수면 이미 일어난 상태로 시작(앞 샷에서 이어짐), null이면 없음
  inputAt?: number | null;
  typeAt?: number | null;
  typeLines?: number;
  sendAt?: number | null;
  buildAt?: number | null;
  misalignAt?: number | null;
  realignAt?: number | null;
};

export type KineticTextLayer = {
  type: "kinetic_text";
  text: string;
  x: number; // 중심 x
  y: number; // 기준선 위쪽 y
  size?: number;
  weight?: "Bold" | "Medium" | "Light";
  color?: string;
  start?: number;
  mode?: "word_rise" | "mask_up";
  highlight?: string[];
  highlightColor?: string;
  maxWidth?: number;
};

export type NotifyLayer = { type: "notify_card"; x: number; y: number; start?: number; accent?: string };

// 로고 스팅거: 예고(선) → 드러남 → 정착. 로고 이미지는 비율·색을 건드리지 않는다
export type LogoStingLayer = {
  type: "logo_sting";
  src: string; // assets 안 로고 파일(투명 PNG 권장)
  x: number; // 중심 x
  y: number; // 중심 y
  width: number;
  start?: number;
  accent?: string; // 예고 선 색
  tagline?: string;
  taglineColor?: string;
};

// 데이터 막대: 0에서 시작하는 선형 축만. 값·단위·출처를 화면에 표시한다
export type DataBarsLayer = {
  type: "data_bars";
  box: Box;
  items: { label: string; value: number; highlight?: boolean }[];
  unit: string;
  source: string;
  title?: string;
  max?: number;
  orientation?: "vertical" | "horizontal";
  start?: number;
  color?: string; // 글자
  barColor?: string;
  highlightColor?: string;
  mapping?: { track_px: number; max: number }; // ap motion이 넣는 값→픽셀 매핑
};

// 전체화면 키네틱: 구(의미 단위)마다 화면을 채우고, 다음 구가 오면 위로 밀려 나간다
export type KineticFullLayer = {
  type: "kinetic_full";
  phrases: { text: string; at: number; highlight?: string[] }[]; // text의 "\n"은 줄바꿈
  color?: string;
  highlightColor?: string;
  maxSize?: number;
  y?: number; // 중심 y (기본 화면 중앙)
};

export type Layer = AppScreenLayer | KineticTextLayer | NotifyLayer | LogoStingLayer | DataBarsLayer | KineticFullLayer;

export type SceneProps = {
  width: number;
  height: number;
  fps: number;
  durationInFrames: number;
  background?: { type: "image"; src: string } | { type: "color"; value: string } | { type: "transparent" };
  camera?: Camera;
  layers: Layer[];
};
