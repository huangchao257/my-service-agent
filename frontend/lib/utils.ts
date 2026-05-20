/**
 * 工具函数 — Tailwind CSS 类名合并
 *
 * 使用 clsx 和 tailwind-merge 避免类名冲突。
 */
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}