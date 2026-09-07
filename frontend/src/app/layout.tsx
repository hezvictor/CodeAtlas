import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "CodeAtlas", description: "ACM/OI 私人知识库 AI 助教" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="zh-CN"><body>{children}</body></html>; }
