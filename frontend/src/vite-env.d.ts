/// <reference types="vite/client" />

declare module "*.css" {
  const content: { [className: string]: string };
  export default content;
}

declare module "@vue-flow/core/dist/style.css";
declare module "@vue-flow/controls/dist/style.css";
