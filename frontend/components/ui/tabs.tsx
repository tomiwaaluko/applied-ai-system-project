"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export function Tabs({ tabs }: { tabs: { value: string; label: string; content: React.ReactNode }[] }) {
  const [active, setActive] = React.useState(tabs[0]?.value);
  const current = tabs.find((tab) => tab.value === active) ?? tabs[0];
  return (
    <div>
      <div className="mb-5 flex flex-wrap gap-2 rounded-2xl bg-zinc-900 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActive(tab.value)}
            className={cn(
              "rounded-xl px-4 py-2 text-sm font-medium text-zinc-400 transition",
              active === tab.value && "bg-white text-zinc-950",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div>{current?.content}</div>
    </div>
  );
}
