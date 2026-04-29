import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("inline-flex rounded-full border border-white/10 bg-white/10 px-2.5 py-1 text-xs font-medium text-zinc-100", className)} {...props} />;
}
