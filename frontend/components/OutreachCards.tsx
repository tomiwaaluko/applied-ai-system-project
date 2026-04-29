"use client";

import type { OutreachDraft } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

function CopyButton({ text }: { text: string }) {
  return <Button onClick={() => navigator.clipboard.writeText(text)}>Copy</Button>;
}

export function OutreachCards({ outreach }: { outreach: OutreachDraft }) {
  const emailText = `${outreach.cold_email_subject}\n\n${outreach.cold_email_body}`;
  const words = outreach.cold_email_body.trim().split(/\s+/).filter(Boolean).length;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">LinkedIn DM</h3>
          <Badge>{outreach.linkedin_dm.length}/300 chars</Badge>
        </div>
        <p className="min-h-36 whitespace-pre-wrap rounded-2xl bg-black/30 p-4 text-sm leading-6 text-zinc-200">{outreach.linkedin_dm}</p>
        <div className="mt-4"><CopyButton text={outreach.linkedin_dm} /></div>
      </Card>
      <Card>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Cold Email</h3>
          <Badge>{outreach.tone} / {words} words</Badge>
        </div>
        <p className="font-medium text-emerald-200">{outreach.cold_email_subject}</p>
        <p className="mt-3 min-h-36 whitespace-pre-wrap rounded-2xl bg-black/30 p-4 text-sm leading-6 text-zinc-200">{outreach.cold_email_body}</p>
        <div className="mt-4"><CopyButton text={emailText} /></div>
      </Card>
    </div>
  );
}
