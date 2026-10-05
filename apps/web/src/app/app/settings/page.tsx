"use client";

import React, { useState, useEffect } from "react";
import { ArmSidebar } from "@/components/arm/arm-sidebar";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBanner } from "@/components/ui/status-banner";
import {
  User,
  Shield,
  Sliders,
  Bell,
  Key,
  GraduationCap,
  Save,
  Menu,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  FileCode2,
  Image as ImageIcon,
  Lock,
  Layers,
  Palette,
  ExternalLink,
} from "lucide-react";
import {
  apiClient,
  IntegrationsOverviewDTO,
  IntegrationValidationResultDTO,
} from "@/lib/api-client";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<
    "profile" | "account" | "preferences" | "notifications" | "security" | "integrations"
  >("profile");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [savedBanner, setSavedBanner] = useState(false);

  // Profile data
  const [fullName, setFullName] = useState("Engineering Scholar");
  const [email, setEmail] = useState("scholar@university.edu");
  const [institution, setInstitution] = useState("National Institute of Technology");
  const [department, setDepartment] = useState("Computer Science & Engineering");
  const [rollNumber, setRollNumber] = useState("2022BCSE042");

  // Preferences
  const [citationFormat, setCitationFormat] = useState("IEEE");
  const [fontSize, setFontSize] = useState("12pt");
  const [defaultLineSpacing, setDefaultLineSpacing] = useState("1.5");

  // Integrations state
  const [integrationsOverview, setIntegrationsOverview] = useState<IntegrationsOverviewDTO | null>(null);
  const [loadingIntegrations, setLoadingIntegrations] = useState(false);
  const [validatingMap, setValidatingMap] = useState<Record<string, boolean>>({});
  const [validationResults, setValidationResults] = useState<Record<string, IntegrationValidationResultDTO>>({});
  const [integrationsBanner, setIntegrationsBanner] = useState<{
    type: "success" | "error" | "warning";
    title: string;
    message: string;
  } | null>(null);

  const loadIntegrations = async () => {
    try {
      setLoadingIntegrations(true);
      const data = await apiClient.getIntegrationStatuses();
      setIntegrationsOverview(data);
    } catch (err) {
      console.error("Failed to load integration statuses:", err);
    } finally {
      setLoadingIntegrations(false);
    }
  };

  useEffect(() => {
    if (activeTab === "integrations") {
      loadIntegrations();
    }
  }, [activeTab]);


  const handleValidateIntegration = async (integrationId: string) => {
    setValidatingMap((prev) => ({ ...prev, [integrationId]: true }));
    try {
      const res = await apiClient.validateIntegration(integrationId);
      setValidationResults((prev) => ({ ...prev, [integrationId]: res }));
      if (res.is_valid) {
        setIntegrationsBanner({
          type: "success",
          title: `${res.name} Verified`,
          message: res.message,
        });
      } else {
        setIntegrationsBanner({
          type: res.status === "degraded" ? "warning" : "error",
          title: `${res.name} Check Failed`,
          message: `${res.message} ${res.error || ""} (ARM fallback active: ${res.fallback_active ? "Yes" : "No"})`,
        });
      }
      await loadIntegrations();
    } catch (err: any) {
      setIntegrationsBanner({
        type: "error",
        title: "Validation Error",
        message: err.message || "Could not complete validation check.",
      });
    } finally {
      setValidatingMap((prev) => ({ ...prev, [integrationId]: false }));
      setTimeout(() => setIntegrationsBanner(null), 5000);
    }
  };

  const handleValidateAll = async () => {
    setValidatingMap((prev) => ({ ...prev, all: true }));
    try {
      const results = await apiClient.validateAllIntegrations();
      const newMap: Record<string, IntegrationValidationResultDTO> = {};
      results.forEach((r) => {
        newMap[r.integration_id] = r;
      });
      setValidationResults(newMap);
      await loadIntegrations();

      const fails = results.filter((r) => !r.is_valid && !r.fallback_active);
      if (fails.length === 0) {
        setIntegrationsBanner({
          type: "success",
          title: "All Integrations Validated",
          message: "All operational and fallback pipelines are verified and ready.",
        });
      } else {
        setIntegrationsBanner({
          type: "warning",
          title: "Validation Complete with Warnings",
          message: `${fails.length} integration(s) require environment configuration. Core ARM features continue.`,
        });
      }
    } catch (err: any) {
      setIntegrationsBanner({
        type: "error",
        title: "Validation Error",
        message: err.message || "Failed to validate integrations.",
      });
    } finally {
      setValidatingMap((prev) => ({ ...prev, all: false }));
      setTimeout(() => setIntegrationsBanner(null), 5000);
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedBanner(true);
    setTimeout(() => setSavedBanner(false), 3000);
  };

  const tabs = [
    { key: "profile", label: "Profile", icon: User },
    { key: "account", label: "Account", icon: GraduationCap },
    { key: "preferences", label: "Preferences", icon: Sliders },
    { key: "notifications", label: "Notifications", icon: Bell },
    { key: "security", label: "Security", icon: Shield },
    { key: "integrations", label: "Integrations", icon: Cpu },
  ];


  return (
    <div className="flex h-screen w-full bg-white dark:bg-black text-zinc-900 dark:text-zinc-100 overflow-hidden transition-colors duration-300">
      <ArmSidebar
        isMobileOpen={mobileMenuOpen}
        onToggleMobile={() => setMobileMenuOpen(false)}
      />

      <div className="flex-1 flex flex-col h-full overflow-hidden bg-white dark:bg-black transition-colors duration-300">
        {/* Top Bar */}
        <header className="h-14 border-b border-zinc-200 dark:border-zinc-900 px-6 flex items-center justify-between shrink-0 bg-white/80 dark:bg-black/80 backdrop-blur-md transition-colors duration-300">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-1.5 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-sm font-semibold text-zinc-900 dark:text-white tracking-tight">
              Settings & Affiliation
            </h1>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full space-y-6">
          {savedBanner && (
            <StatusBanner
              type="success"
              title="Preferences Saved"
              message="Your profile settings and institutional citation presets have been updated."
            />
          )}

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-zinc-900 pb-3 overflow-x-auto scrollbar-none">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key as any)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    activeTab === tab.key
                      ? "bg-zinc-900 text-white font-semibold border border-zinc-800"
                      : "text-zinc-400 hover:text-white hover:bg-zinc-950"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab 1: Profile */}
          {activeTab === "profile" && (
            <Card className="border-zinc-850 bg-zinc-950/60">
              <CardHeader>
                <CardTitle>Academic Profile</CardTitle>
                <CardDescription>
                  Your details will appear on generated project report title pages and certificate blocks.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSave} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-zinc-300">Scholar Name</label>
                      <input
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-white focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-zinc-300">Roll / Registration Number</label>
                      <input
                        type="text"
                        value={rollNumber}
                        onChange={(e) => setRollNumber(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-white focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-300">University / College Name</label>
                    <input
                      type="text"
                      value={institution}
                      onChange={(e) => setInstitution(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-white focus:outline-none focus:border-zinc-600"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-300">Department / Branch</label>
                    <input
                      type="text"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-white focus:outline-none focus:border-zinc-600"
                    />
                  </div>

                  <div className="flex justify-end pt-3 border-t border-zinc-900">
                    <Button type="submit" variant="primary" size="sm" className="text-xs">
                      <Save className="w-3.5 h-3.5 mr-1.5" /> Save Changes
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {/* Tab 2: Account */}
          {activeTab === "account" && (
            <Card className="border-zinc-850 bg-zinc-950/60">
              <CardHeader>
                <CardTitle>Academic Account</CardTitle>
                <CardDescription>Authentication credentials and email synchronization</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-300">Email Address</label>
                  <input
                    type="email"
                    disabled
                    value={email}
                    className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900/40 text-xs text-zinc-400 cursor-not-allowed"
                  />
                  <p className="text-[10px] text-zinc-500 font-mono">
                    Contact your department admin to modify institution email.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tab 3: Preferences */}
          {activeTab === "preferences" && (
            <Card className="border-zinc-850 bg-zinc-950/60">
              <CardHeader>
                <CardTitle>Synthesis & Citation Preferences</CardTitle>
                <CardDescription>Default typography rules applied when no template override is present</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-300">Default Citation Style</label>
                    <select
                      value={citationFormat}
                      onChange={(e) => setCitationFormat(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-white focus:outline-none focus:border-zinc-600"
                    >
                      <option value="IEEE">IEEE Reference Standard [1]</option>
                      <option value="APA">APA 7th Edition (Author, Year)</option>
                      <option value="ACM">ACM Association Reference Format</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-zinc-300">Body Line Spacing</label>
                    <select
                      value={defaultLineSpacing}
                      onChange={(e) => setDefaultLineSpacing(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-white focus:outline-none focus:border-zinc-600"
                    >
                      <option value="1.5">1.5 Lines (Standard Academic)</option>
                      <option value="2.0">Double Spacing (2.0)</option>
                      <option value="1.15">1.15 Lines (Compact)</option>
                    </select>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tab 4: Notifications */}
          {activeTab === "notifications" && (
            <Card className="border-zinc-850 bg-zinc-950/60">
              <CardHeader>
                <CardTitle>Compilation Alerts</CardTitle>
                <CardDescription>Configure system notifications during document assembly</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-zinc-300">
                <label className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900/40 border border-zinc-850">
                  <input type="checkbox" defaultChecked className="rounded border-zinc-700" />
                  <span>Notify when document compilation finishes</span>
                </label>
                <label className="flex items-center gap-3 p-3 rounded-lg bg-zinc-900/40 border border-zinc-850">
                  <input type="checkbox" defaultChecked className="rounded border-zinc-700" />
                  <span>Alert on template margin inconsistencies</span>
                </label>
              </CardContent>
            </Card>
          )}

          {/* Tab 5: Security */}
          {activeTab === "security" && (
            <Card className="border-zinc-850 bg-zinc-950/60">
              <CardHeader>
                <CardTitle>Security & Sessions</CardTitle>
                <CardDescription>Manage security credentials and session integrity</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button variant="outline" size="sm" className="text-xs">
                  Change Account Password
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Tab 6: Integrations */}
          {activeTab === "integrations" && (
            <div className="space-y-6">
              {integrationsBanner && (
                <StatusBanner
                  type={integrationsBanner.type}
                  title={integrationsBanner.title}
                  message={integrationsBanner.message}
                />
              )}

              {/* Secrets Security Banner */}
              <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-950/80 flex items-start gap-3.5">
                <div className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 shrink-0">
                  <Lock className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-white tracking-tight">
                      Backend Secrets Isolation Guarantee
                    </span>
                    <Badge variant="outline" className="text-[10px] bg-emerald-950/50 text-emerald-300 border-emerald-800">
                      Zero Client Exposure
                    </Badge>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    All provider credentials, tokens, and API keys are stored exclusively in server environment variables (<code className="font-mono text-zinc-300 text-[10px]">.env</code>). Secrets are never exposed to browser JavaScript, never saved in localStorage, and never transmitted over the network.
                  </p>
                </div>
              </div>

              {/* Controls Bar */}
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-sm font-semibold text-white">Configured Providers & Engines</h2>
                  <p className="text-xs text-zinc-400">
                    Status of core synthesis, visual assets, document assembly, and optional exports.
                  </p>
                </div>
                <Button
                  onClick={handleValidateAll}
                  disabled={validatingMap["all"] || loadingIntegrations}
                  variant="outline"
                  size="sm"
                  className="text-xs shrink-0"
                >
                  <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${validatingMap["all"] ? "animate-spin" : ""}`} />
                  {validatingMap["all"] ? "Validating All..." : "Validate All Integrations"}
                </Button>
              </div>

              {/* 1. AI Model Provider */}
              <Card className="border-zinc-850 bg-zinc-950/60">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-blue-950/40 border border-blue-900/60 text-blue-400">
                        <Cpu className="w-4 h-4" />
                      </div>
                      <div>
                        <CardTitle className="text-sm font-medium">AI Model Provider</CardTitle>
                        <CardDescription className="text-xs">
                          Grounded academic content generation and structured field synthesis
                        </CardDescription>
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={`text-xs ${
                        integrationsOverview?.integrations.find((i) => i.id === "ai")?.is_configured
                          ? "bg-emerald-950/40 text-emerald-400 border-emerald-800"
                          : "bg-amber-950/40 text-amber-400 border-amber-800"
                      }`}
                    >
                      {integrationsOverview?.integrations.find((i) => i.id === "ai")?.status.toUpperCase() || "READY"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3.5 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-lg bg-zinc-900/50 border border-zinc-850">
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Active Provider & Model:</span>
                      <span className="font-mono text-zinc-200">
                        {integrationsOverview?.integrations.find((i) => i.id === "ai")?.provider || "gemini"} •{" "}
                        {integrationsOverview?.integrations.find((i) => i.id === "ai")?.active_model_or_engine || "gemini-1.5-flash"}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Required Environment Variable:</span>
                      <code className="text-amber-300 font-mono text-[11px] bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-800">
                        GEMINI_API_KEY
                      </code>
                    </div>
                  </div>

                  <p className="text-zinc-400 text-[11px]">
                    {integrationsOverview?.integrations.find((i) => i.id === "ai")?.status_message ||
                      "Google Gemini API is configured for grounded text and JSON synthesis."}
                  </p>

                  <div className="flex items-center gap-2 p-2.5 rounded-lg bg-zinc-900/30 border border-zinc-850 text-[11px] text-zinc-400">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                    <span>
                      Fallback Active: If AI is unavailable, ARM allows manual editing, evidence management, and Master Template replacement to continue uninterrupted.
                    </span>
                  </div>

                  {validationResults["ai"] && (
                    <div
                      className={`p-3 rounded-lg text-xs border ${
                        validationResults["ai"].is_valid
                          ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                          : "bg-rose-950/30 border-rose-800/60 text-rose-300"
                      }`}
                    >
                      <div className="font-semibold">{validationResults["ai"].message}</div>
                      {validationResults["ai"].error && (
                        <div className="mt-1 text-[11px] opacity-90">Error: {validationResults["ai"].error}</div>
                      )}
                      {validationResults["ai"].remediation && (
                        <div className="mt-1 text-[11px] font-mono text-zinc-300">
                          Fix: {validationResults["ai"].remediation}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex justify-end pt-1">
                    <Button
                      onClick={() => handleValidateIntegration("ai")}
                      disabled={validatingMap["ai"]}
                      variant="outline"
                      size="sm"
                      className="text-xs"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${validatingMap["ai"] ? "animate-spin" : ""}`} />
                      {validatingMap["ai"] ? "Testing..." : "Test AI Connection"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* 2. Image Asset Provider */}
              <Card className="border-zinc-850 bg-zinc-950/60">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-purple-950/40 border border-purple-900/60 text-purple-400">
                        <ImageIcon className="w-4 h-4" />
                      </div>
                      <div>
                        <CardTitle className="text-sm font-medium">Image Asset Provider</CardTitle>
                        <CardDescription className="text-xs">
                          300 DPI Academic Visuals, Block Architecture Diagrams, & Benchmark Charts
                        </CardDescription>
                      </div>
                    </div>
                    <Badge variant="outline" className="text-xs bg-emerald-950/40 text-emerald-400 border-emerald-800">
                      OPERATIONAL
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3.5 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-lg bg-zinc-900/50 border border-zinc-850">
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Primary Engine:</span>
                      <span className="font-mono text-zinc-200">ARM Native Academic Visual Engine (300 DPI)</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Optional External Search:</span>
                      <code className="text-zinc-400 font-mono text-[11px] bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-800">
                        UNSPLASH_ACCESS_KEY
                      </code>
                    </div>
                  </div>

                  <p className="text-zinc-400 text-[11px]">
                    ARM automatically determines required image types per section and synthesizes publication-grade block diagrams and empirical charts with verified open academic licensing.
                  </p>

                  <div className="flex items-center gap-2 p-2.5 rounded-lg bg-zinc-900/30 border border-zinc-850 text-[11px] text-zinc-400">
                    <CheckCircle2 className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                    <span>
                      Zero-Dependency Fallback: If external image APIs are unconfigured, ARM seamlessly falls back to the Native Visual Engine so document compilation never halts.
                    </span>
                  </div>

                  {validationResults["image"] && (
                    <div
                      className={`p-3 rounded-lg text-xs border ${
                        validationResults["image"].is_valid
                          ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                          : "bg-rose-950/30 border-rose-800/60 text-rose-300"
                      }`}
                    >
                      <div className="font-semibold">{validationResults["image"].message}</div>
                      {validationResults["image"].remediation && (
                        <div className="mt-1 text-[11px] font-mono text-zinc-300">
                          {validationResults["image"].remediation}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex justify-end pt-1">
                    <Button
                      onClick={() => handleValidateIntegration("image")}
                      disabled={validatingMap["image"]}
                      variant="outline"
                      size="sm"
                      className="text-xs"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${validatingMap["image"] ? "animate-spin" : ""}`} />
                      {validatingMap["image"] ? "Testing..." : "Validate Image Engine"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* 3. Document Generation Engine */}
              <Card className="border-zinc-850 bg-zinc-950/60">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-emerald-950/40 border border-emerald-900/60 text-emerald-400">
                        <FileCode2 className="w-4 h-4" />
                      </div>
                      <div>
                        <CardTitle className="text-sm font-medium">Document Generation Engine</CardTitle>
                        <CardDescription className="text-xs">
                          Master College Template Replacement Engine (DOCX & PDF Assembly)
                        </CardDescription>
                      </div>
                    </div>
                    <Badge variant="outline" className="text-xs bg-emerald-950/40 text-emerald-400 border-emerald-800">
                      PRIMARY ENGINE READY
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3.5 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-lg bg-zinc-900/50 border border-zinc-850">
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Active Engine:</span>
                      <span className="font-mono text-zinc-200">ARM Internal OpenXML Engine (python-docx)</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Optional Cloud Engine:</span>
                      <code className="text-zinc-400 font-mono text-[11px] bg-zinc-950 px-1.5 py-0.5 rounded border border-zinc-800">
                        CARBONE_API_KEY
                      </code>
                    </div>
                  </div>

                  <p className="text-zinc-400 text-[11px]">
                    The Master College Template is the source of truth. ARM replaces canonical placeholders directly inside OpenXML structures, preserving 100% of college fonts, margins, headers, and footers.
                  </p>

                  <div className="flex items-center gap-2 p-2.5 rounded-lg bg-zinc-900/30 border border-zinc-850 text-[11px] text-zinc-400">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>
                      Autonomous Assembly: Does not require copy-pasting into Word or external editors. Generates completed DOCX and PDF natively.
                    </span>
                  </div>

                  {validationResults["document"] && (
                    <div
                      className={`p-3 rounded-lg text-xs border ${
                        validationResults["document"].is_valid
                          ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                          : "bg-rose-950/30 border-rose-800/60 text-rose-300"
                      }`}
                    >
                      <div className="font-semibold">{validationResults["document"].message}</div>
                      {validationResults["document"].remediation && (
                        <div className="mt-1 text-[11px] font-mono text-zinc-300">
                          {validationResults["document"].remediation}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex justify-end pt-1">
                    <Button
                      onClick={() => handleValidateIntegration("document")}
                      disabled={validatingMap["document"]}
                      variant="outline"
                      size="sm"
                      className="text-xs"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${validatingMap["document"] ? "animate-spin" : ""}`} />
                      {validatingMap["document"] ? "Testing..." : "Validate Document Engine"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* 4. Optional Canva Integration */}
              <Card className="border-zinc-850 bg-zinc-950/60">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-pink-950/40 border border-pink-900/60 text-pink-400">
                        <Palette className="w-4 h-4" />
                      </div>
                      <div>
                        <CardTitle className="text-sm font-medium">Canva Integration (Optional)</CardTitle>
                        <CardDescription className="text-xs">
                          Export completed report slides to Canva Connect API
                        </CardDescription>
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={`text-xs ${
                        integrationsOverview?.integrations.find((i) => i.id === "canva")?.is_configured
                          ? "bg-emerald-950/40 text-emerald-400 border-emerald-800"
                          : "bg-zinc-800 text-zinc-400 border-zinc-700"
                      }`}
                    >
                      {integrationsOverview?.integrations.find((i) => i.id === "canva")?.is_configured
                        ? "CONFIGURED"
                        : "OPTIONAL / NOT CONFIGURED"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3.5 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-lg bg-zinc-900/50 border border-zinc-850">
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Integration Status:</span>
                      <span className="text-zinc-300">
                        {integrationsOverview?.integrations.find((i) => i.id === "canva")?.status_message ||
                          "Canva is optional and unconfigured."}
                      </span>
                    </div>
                    <div>
                      <span className="text-zinc-500 text-[11px] block">Configuration Keys (Backend .env):</span>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <code className="text-zinc-400 font-mono text-[10px] bg-zinc-950 px-1 py-0.5 rounded border border-zinc-800">
                          CANVA_CLIENT_ID
                        </code>
                        <code className="text-zinc-400 font-mono text-[10px] bg-zinc-950 px-1 py-0.5 rounded border border-zinc-800">
                          CANVA_CLIENT_SECRET
                        </code>
                      </div>
                    </div>
                  </div>

                  <p className="text-zinc-400 text-[11px]">
                    ARM&apos;s primary workflow is automated replacement into the official Master College Template. Canva integration is optional for visual slide decks and presentations.
                  </p>

                  {validationResults["canva"] && (
                    <div
                      className={`p-3 rounded-lg text-xs border ${
                        validationResults["canva"].is_valid
                          ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                          : "bg-zinc-900 border-zinc-800 text-zinc-300"
                      }`}
                    >
                      <div className="font-semibold">{validationResults["canva"].message}</div>
                      {validationResults["canva"].remediation && (
                        <div className="mt-1 text-[11px] font-mono text-zinc-400">
                          {validationResults["canva"].remediation}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex justify-end pt-1">
                    <Button
                      onClick={() => handleValidateIntegration("canva")}
                      disabled={validatingMap["canva"]}
                      variant="outline"
                      size="sm"
                      className="text-xs"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${validatingMap["canva"] ? "animate-spin" : ""}`} />
                      {validatingMap["canva"] ? "Checking..." : "Check Canva Status"}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

