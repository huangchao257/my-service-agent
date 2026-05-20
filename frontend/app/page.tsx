/**
 * 首页重定向 — 直接跳转到 /chat
 */
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/chat");
}