import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

/** 將頁面專屬的控制項放進頂部列（header-meta：搜尋左側文字；header-menu：右側圓形選單） */
export default function HeaderSlot({ slot, children }: { slot: "header-meta" | "header-menu"; children: ReactNode }) {
  const [el, setEl] = useState<HTMLElement | null>(null);
  useEffect(() => setEl(document.getElementById(slot)), [slot]);
  return el ? createPortal(children, el) : null;
}
