import { message } from "ant-design-vue";

export function useClipboard() {
  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      message.success("已复制到剪贴板");
    } catch (err) {
      message.error("复制失败");
    }
  };

  return { copyToClipboard };
}
