import type { Metadata } from "next"; import "./globals.css"; import AppErrorProvider from "../components/AppErrorProvider";
export const metadata: Metadata={title:"CodeAtlas",description:"ACM/OI 私人知识库 AI 助教"};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="zh-CN"><body><AppErrorProvider>{children}</AppErrorProvider></body></html>}