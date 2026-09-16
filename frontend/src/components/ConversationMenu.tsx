"use client";

import { useEffect, useRef } from "react";

export function conversationMenuActions(pinned: boolean) {
  return ["重命名", pinned ? "取消置顶" : "置顶", "多选", "删除"];
}

export type ConversationMenuProps = {
  pinned?: boolean;
  onRename: () => void;
  onTogglePin: () => void;
  onMultiSelect: () => void;
  onDelete: () => void;
  onClose?: () => void;
};

export default function ConversationMenu({ pinned, onRename, onTogglePin, onMultiSelect, onDelete, onClose }: ConversationMenuProps) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (event: MouseEvent) => { if (ref.current && !ref.current.contains(event.target as Node)) onClose?.(); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [onClose]);
  return <div ref={ref} className="conversation-menu" role="menu">
    <button role="menuitem" onClick={() => { onRename(); onClose?.(); }}>✎ 重命名</button>
    <button role="menuitem" onClick={() => { onTogglePin(); onClose?.(); }}>{pinned ? "⌃ 取消置顶" : "⌃ 置顶"}</button>
    <button role="menuitem" onClick={() => { onMultiSelect(); onClose?.(); }}>☷ 多选</button>
    <button role="menuitem" className="danger" onClick={() => { onDelete(); onClose?.(); }}>♲ 删除</button>
  </div>;
}
