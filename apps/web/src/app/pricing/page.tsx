import React from "react";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock, CheckCircle2, ShieldAlert } from "lucide-react";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 flex flex-col transition-colors duration-300">
      <PublicNav />

      <main className="flex-1 max-w-5xl mx-auto px-6 py-20 w-full">
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-16">
          <Badge variant="accent" className="mb-4">
            Under Evaluation
          </Badge>
          <h1 className="text-3xl sm:text-5xl font-light text-zinc-900 dark:text-white tracking-tight mb-4">
            Pricing plans coming soon
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400 text-sm sm:text-base leading-relaxed">
            ARM is currently in technical preview for participating engineering colleges and academic project cohorts. Transparent student quotas and department licensing models will be published shortly.
          </p>
        </div>

        {/* Coming Soon Tier Outline (No fake payment buttons!) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          <Card className="border-zinc-800 bg-zinc-950/60 flex flex-col justify-between">
            <CardHeader>
              <Badge variant="secondary" className="w-fit mb-2 text-[10px]">
                Preview Tier
              </Badge>
              <CardTitle>Individual Scholar</CardTitle>
              <CardDescription>For students working on single-semester major projects</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-zinc-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-500" />
                <span>Custom college template parsing (.docx)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-500" />
                <span>Evidence locker for code & datasets</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-500" />
                <span>Weekly project diary generator</span>
              </div>
            </CardContent>
            <CardFooter>
              <div className="w-full py-2.5 px-4 rounded-lg bg-zinc-900 border border-zinc-800 text-center text-xs font-mono text-zinc-500">
                Tier details in review
              </div>
            </CardFooter>
          </Card>

          <Card className="border-zinc-700 bg-zinc-900/40 relative flex flex-col justify-between">
            <div className="absolute -top-2.5 right-6">
              <Badge variant="success" className="text-[10px]">Cohort Focus</Badge>
            </div>
            <CardHeader>
              <Badge variant="secondary" className="w-fit mb-2 text-[10px]">
                Team Tier
              </Badge>
              <CardTitle>Project Syndicate</CardTitle>
              <CardDescription>For 3–4 member student groups collaborating on a capstone</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-zinc-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-400" />
                <span>Shared team evidence repository</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-400" />
                <span>Multi-chapter synchronized compilation</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-400" />
                <span>Supervisor signature blocks & weekly tracking</span>
              </div>
            </CardContent>
            <CardFooter>
              <div className="w-full py-2.5 px-4 rounded-lg bg-zinc-900 border border-zinc-800 text-center text-xs font-mono text-zinc-500">
                Tier details in review
              </div>
            </CardFooter>
          </Card>

          <Card className="border-zinc-800 bg-zinc-950/60 flex flex-col justify-between">
            <CardHeader>
              <Badge variant="secondary" className="w-fit mb-2 text-[10px]">
                Department
              </Badge>
              <CardTitle>College Department</CardTitle>
              <CardDescription>For universities mandating standard document formats across branches</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-zinc-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-500" />
                <span>Standardized department template enforcement</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-500" />
                <span>Faculty review and approval workflow</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-zinc-500" />
                <span>Dedicated on-premise or cloud storage options</span>
              </div>
            </CardContent>
            <CardFooter>
              <div className="w-full py-2.5 px-4 rounded-lg bg-zinc-900 border border-zinc-800 text-center text-xs font-mono text-zinc-500">
                Institutional pilot in progress
              </div>
            </CardFooter>
          </Card>
        </div>

        {/* Notice Card */}
        <div className="p-5 rounded-xl border border-zinc-850 bg-zinc-950 flex items-start gap-4">
          <Clock className="w-5 h-5 text-zinc-500 shrink-0 mt-0.5" />
          <div className="text-xs text-zinc-400 leading-relaxed">
            <p className="font-semibold text-white mb-1">Preview Period Guarantee</p>
            Students during the initial release period are granted free baseline document synthesis credits to validate compatibility with their respective college guidelines.
          </div>
        </div>
      </main>

      <PublicFooter />
    </div>
  );
}
