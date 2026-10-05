"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  FolderArchive,
  Upload,
  FileCode,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  ShieldCheck,
  Trash2,
  Download,
  AlertCircle,
  CheckCircle2,
  Clock,
  Filter,
  Eye,
  Hash,
  Info
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { apiClient, EvidenceDTO } from "@/lib/api-client";

interface EvidenceLockerProps {
  projectId: string;
  onEvidenceChange?: () => void;
}

const CATEGORIES = [
  { id: "all", label: "All Evidence" },
  { id: "dataset", label: "Datasets / CSV" },
  { id: "code_sample", label: "Code Snippets" },
  { id: "survey_results", label: "Survey & Data" },
  { id: "literature", label: "Literature / Papers" },
  { id: "system_output", label: "Logs & Results" },
  { id: "notes", label: "Notes" },
  { id: "other", label: "Other" },
];

export function EvidenceLocker({ projectId, onEvidenceChange }: EvidenceLockerProps) {
  const [evidenceList, setEvidenceList] = useState<EvidenceDTO[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Upload Form State
  const [uploadCategory, setUploadCategory] = useState<string>("other");
  const [uploadDescription, setUploadDescription] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadEvidence = React.useCallback(async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const cat = selectedCategory === "all" ? undefined : selectedCategory;
      const data = await apiClient.getProjectEvidence(projectId, cat);
      setEvidenceList(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load evidence files.");
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedCategory]);

  useEffect(() => {
    loadEvidence();
  }, [loadEvidence]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];

    // Client-side quick checks
    const allowed = [".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".txt"];
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowed.includes(ext)) {
      setErrorMsg(`File extension '${ext}' is not supported. Supported: ${allowed.join(", ")}`);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size === 0) {
      setErrorMsg("File is empty (0 bytes).");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMsg("File size exceeds maximum allowed limit of 25MB.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    try {
      setUploading(true);
      setErrorMsg(null);
      setSuccessMsg(null);

      const created = await apiClient.uploadProjectEvidence(
        projectId,
        file,
        uploadCategory,
        uploadDescription.trim() || undefined
      );

      setEvidenceList((prev) => [created, ...prev]);
      setSuccessMsg(`Successfully uploaded and verified '${file.name}'.`);
      setUploadDescription("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (onEvidenceChange) onEvidenceChange();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to upload evidence.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (evidenceId: string, fileName: string) => {
    if (!confirm(`Are you sure you want to delete '${fileName}' from the Evidence Locker?`)) {
      return;
    }
    try {
      await apiClient.deleteProjectEvidence(projectId, evidenceId);
      setEvidenceList((prev) => prev.filter((e) => e.id !== evidenceId));
      setSuccessMsg(`Deleted '${fileName}'.`);
      if (onEvidenceChange) onEvidenceChange();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to delete evidence.");
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getFileIcon = (mimeOrType: string, filename: string) => {
    const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
    if (ext === ".csv" || ext === ".xlsx") {
      return <FileSpreadsheet className="w-5 h-5 text-emerald-600" />;
    }
    if (ext === ".png" || ext === ".jpg" || ext === ".jpeg") {
      return <ImageIcon className="w-5 h-5 text-blue-600" />;
    }
    if (ext === ".txt" || mimeOrType.includes("code")) {
      return <FileCode className="w-5 h-5 text-purple-600" />;
    }
    return <FileText className="w-5 h-5 text-indigo-600" />;
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-100 rounded-xl">
        <div className="flex items-start gap-3">
          <div className="p-2.5 bg-emerald-600 text-white rounded-lg shadow-sm">
            <FolderArchive className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Academic Evidence Locker</h2>
            <p className="text-sm text-slate-600">
              Securely store experimental data, code samples, survey results, and literature with cryptographic verification.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 bg-white px-3.5 py-2 rounded-lg border border-emerald-200 shadow-sm text-xs font-medium text-emerald-800">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          SHA-256 Tamper Protected
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="flex items-center gap-2 p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          {successMsg}
        </div>
      )}

      {errorMsg && (
        <div className="flex items-center gap-2 p-3.5 bg-red-50 border border-red-200 text-red-800 rounded-lg text-sm">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          {errorMsg}
        </div>
      )}

      {/* Upload Zone */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-slate-800 flex items-center gap-2">
            <Upload className="w-4 h-4 text-emerald-600" />
            Upload Supporting Academic Evidence
          </CardTitle>
          <CardDescription>
            Supported: PDF, DOCX, PPTX, XLSX, CSV, PNG, JPG, TXT (up to 25MB). Evidence is treated strictly as verified passive data.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Evidence Category
              </label>
              <select
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value)}
                className="w-full px-3 py-1.5 border rounded-md border-slate-300 text-sm focus:outline-none"
              >
                <option value="dataset">Dataset / Benchmark CSV</option>
                <option value="code_sample">Code Snippet / Implementation</option>
                <option value="survey_results">Survey & Experimental Results</option>
                <option value="literature">Literature / Research Paper</option>
                <option value="system_output">System Log / Execution Output</option>
                <option value="notes">Guide Feedback / Notes</option>
                <option value="other">Other Academic File</option>
              </select>
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Context / Description (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Training loss convergence curve over 500 epochs"
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                className="w-full px-3 py-1.5 border rounded-md border-slate-300 text-sm focus:outline-none"
              />
            </div>
          </div>

          <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-emerald-500 transition-colors bg-slate-50/50">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
              id="evidence-file-input"
              accept=".pdf,.docx,.pptx,.xlsx,.csv,.png,.jpg,.jpeg,.txt"
            />
            <label
              htmlFor="evidence-file-input"
              className="cursor-pointer flex flex-col items-center justify-center space-y-2"
            >
              <div className="p-3 bg-white border border-slate-200 rounded-full shadow-sm">
                <Upload className="w-6 h-6 text-slate-500" />
              </div>
              <div className="text-sm font-medium text-slate-800">
                {uploading ? "Uploading & Verifying Hash..." : "Click or drag file here to deposit into Evidence Locker"}
              </div>
              <div className="text-xs text-slate-500">
                Automatic SHA-256 fingerprinting ensures tamper-free provenance.
              </div>
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Filter and Evidence List */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 overflow-x-auto py-1">
            <Filter className="w-4 h-4 text-slate-400 mr-1" />
            {CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                  selectedCategory === cat.id
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <div className="text-xs text-slate-500">
            Showing {evidenceList.length} {evidenceList.length === 1 ? "file" : "files"}
          </div>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            <Clock className="w-5 h-5 mx-auto mb-2 animate-spin text-emerald-600" />
            Loading Evidence Locker files...
          </div>
        ) : evidenceList.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="p-10 text-center space-y-2">
              <FolderArchive className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="font-semibold text-slate-700">No Evidence Deposited Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Upload benchmark tables, code files, or architectural diagrams to support report citations and factual generation.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {evidenceList.map((item) => (
              <Card key={item.id} className="hover:shadow-sm transition-shadow">
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="p-2 bg-slate-100 rounded-lg flex-shrink-0 mt-0.5">
                        {getFileIcon(item.file_type || "", item.file_name)}
                      </div>
                      <div className="min-w-0">
                        <h4 className="font-semibold text-sm text-slate-900 truncate" title={item.file_name}>
                          {item.file_name}
                        </h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Badge variant="secondary" className="text-[10px] uppercase">
                            {item.category || "other"}
                          </Badge>
                          <span className="text-xs text-slate-400">
                            {formatFileSize(item.file_size_bytes)}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <a
                        href={apiClient.getEvidenceDownloadUrl(projectId, item.id)}
                        download={item.file_name}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
                        title="Download Evidence File"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                      <button
                        type="button"
                        onClick={() => handleDelete(item.id, item.file_name)}
                        className="p-1.5 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-md transition-colors"
                        title="Delete File"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {item.description && (
                    <p className="text-xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-100">
                      {item.description}
                    </p>
                  )}

                  {item.sha256_hash && (
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono bg-slate-50 px-2 py-1 rounded">
                      <Hash className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                      <span className="truncate">SHA-256: {item.sha256_hash}</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
