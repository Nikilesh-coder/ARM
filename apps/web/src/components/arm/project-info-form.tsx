"use client";

import React, { useState, useEffect } from "react";
import {
  BookOpen,
  GraduationCap,
  Users,
  CheckCircle2,
  AlertCircle,
  Save,
  Plus,
  Trash2,
  Edit2,
  Clock,
  Sparkles,
  Info
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { apiClient, ProjectDTO, ProjectMemberDTO, ProjectReadinessDTO } from "@/lib/api-client";

interface ProjectInfoFormProps {
  projectId: string;
  onUpdated?: () => void;
}

export function ProjectInfoForm({ projectId, onUpdated }: ProjectInfoFormProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form State
  const [form, setForm] = useState<Partial<ProjectDTO>>({
    title: "",
    project_type: "capstone",
    academic_year: "2026-2027",
    department: "",
    institution: "",
    semester: "",
    guide_name: "",
    problem_statement: "",
    objectives: "",
    scope: "",
    methodology: "",
    expected_outcome: "",
    actual_outcome: "",
    additional_notes: "",
    is_team_project: false,
    tech_stack: [],
  });

  const [techStackInput, setTechStackInput] = useState("");
  const [members, setMembers] = useState<ProjectMemberDTO[]>([]);
  const [readiness, setReadiness] = useState<ProjectReadinessDTO | null>(null);

  // Member Modal / Add State
  const [newMember, setNewMember] = useState({ name: "", roll_number: "", email: "", role: "Member" });
  const [addingMember, setAddingMember] = useState(false);

  const fetchData = React.useCallback(async () => {
    try {
      setLoading(true);
      const [proj, memList, read] = await Promise.all([
        apiClient.getProject(projectId),
        apiClient.getProjectMembers(projectId).catch(() => []),
        apiClient.getProjectReadiness(projectId).catch(() => null),
      ]);

      setForm({
        title: proj.title || "",
        project_type: proj.project_type || "capstone",
        academic_year: proj.academic_year || "2026-2027",
        department: proj.department || "",
        institution: proj.institution || "",
        semester: proj.semester || "",
        guide_name: proj.guide_name || "",
        problem_statement: proj.problem_statement || "",
        objectives: proj.objectives || "",
        scope: proj.scope || "",
        methodology: proj.methodology || "",
        expected_outcome: proj.expected_outcome || "",
        actual_outcome: proj.actual_outcome || "",
        additional_notes: proj.additional_notes || "",
        is_team_project: proj.is_team_project || false,
        tech_stack: proj.tech_stack || [],
      });
      setTechStackInput(proj.tech_stack ? proj.tech_stack.join(", ") : "");
      setMembers(memList);
      setReadiness(read);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load project details.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    try {
      setSaving(true);
      setErrorMsg(null);
      setSuccessMsg(null);

      const parsedTech = techStackInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const payload: Partial<ProjectDTO> = {
        ...form,
        tech_stack: parsedTech,
      };

      await apiClient.updateProject(projectId, payload);
      const updatedReadiness = await apiClient.getProjectReadiness(projectId).catch(() => null);
      setReadiness(updatedReadiness);
      setSuccessMsg("Academic project information saved successfully.");
      if (onUpdated) onUpdated();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save project information.");
    } finally {
      setSaving(false);
    }
  };

  const handleAddMember = async () => {
    if (!newMember.name.trim()) return;
    try {
      setAddingMember(true);
      const created = await apiClient.addProjectMember(projectId, newMember);
      setMembers((prev) => [...prev, created]);
      setNewMember({ name: "", roll_number: "", email: "", role: "Member" });
      const updatedReadiness = await apiClient.getProjectReadiness(projectId).catch(() => null);
      setReadiness(updatedReadiness);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to add member.");
    } finally {
      setAddingMember(false);
    }
  };

  const handleDeleteMember = async (memberId: string) => {
    try {
      await apiClient.deleteProjectMember(projectId, memberId);
      setMembers((prev) => prev.filter((m) => m.id !== memberId));
      const updatedReadiness = await apiClient.getProjectReadiness(projectId).catch(() => null);
      setReadiness(updatedReadiness);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to remove member.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-500">
        <Clock className="w-5 h-5 mr-2 animate-spin text-blue-600" />
        Loading Project Information...
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header & Readiness Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl">
        <div className="flex items-start gap-3">
          <div className="p-2.5 bg-blue-600 text-white rounded-lg shadow-sm">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Project Information & Scope</h2>
            <p className="text-sm text-slate-600">
              The foundational source of truth for all academic chapters, methodology, and citations.
            </p>
          </div>
        </div>

        {readiness && (
          <div className="flex items-center gap-3 bg-white px-4 py-2.5 rounded-lg border border-blue-200 shadow-sm">
            <div className="text-right">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
                Readiness Score
              </span>
              <span className="text-lg font-bold text-blue-700">
                {readiness.completion_percentage}%
              </span>
            </div>
            <div className="w-12 h-12 relative flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-slate-100"
                  strokeWidth="3.5"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className="text-blue-600 transition-all duration-500 ease-out"
                  strokeDasharray={`${readiness.completion_percentage}, 100`}
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
            </div>
          </div>
        )}
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

      <form onSubmit={handleSave} className="space-y-6">
        {/* Academic Details Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-800">
              <GraduationCap className="w-5 h-5 text-indigo-600" />
              Academic Institutional Details
            </CardTitle>
            <CardDescription>
              Details needed for the title page, certificate, declaration, and acknowledgment.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Report / Project Title *
                </label>
                <input
                  type="text"
                  required
                  value={form.title || ""}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g. Autonomous Real-Time Traffic Optimization using Deep Q-Learning"
                  className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Faculty Guide / Supervisor Name *
                </label>
                <input
                  type="text"
                  value={form.guide_name || ""}
                  onChange={(e) => setForm({ ...form, guide_name: e.target.value })}
                  placeholder="e.g. Dr. A. K. Sharma, Professor"
                  className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Department / Branch
                </label>
                <input
                  type="text"
                  value={form.department || ""}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                  placeholder="e.g. Department of Computer Science & Engineering"
                  className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Institution / College Name
                </label>
                <input
                  type="text"
                  value={form.institution || ""}
                  onChange={(e) => setForm({ ...form, institution: e.target.value })}
                  placeholder="e.g. National Institute of Technology"
                  className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                    Semester
                  </label>
                  <input
                    type="text"
                    value={form.semester || ""}
                    onChange={(e) => setForm({ ...form, semester: e.target.value })}
                    placeholder="e.g. 8th Semester"
                    className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                    Academic Year
                  </label>
                  <input
                    type="text"
                    value={form.academic_year || ""}
                    onChange={(e) => setForm({ ...form, academic_year: e.target.value })}
                    placeholder="2026-2027"
                    className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Project Classification
                </label>
                <select
                  value={form.project_type || "capstone"}
                  onChange={(e) => setForm({ ...form, project_type: e.target.value })}
                  className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="capstone">Capstone / Final Year Project</option>
                  <option value="mini_project">Mini Project</option>
                  <option value="thesis">Master / Doctoral Thesis</option>
                  <option value="internship">Internship / Industry Report</option>
                  <option value="weekly_lab">Weekly Lab / Practical</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Project Scope & Engineering Content */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-800">
              <Info className="w-5 h-5 text-blue-600" />
              Problem Definition & Scope
            </CardTitle>
            <CardDescription>
              Core academic foundation used by the writing pipeline to maintain factual fidelity.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Problem Statement *
              </label>
              <textarea
                rows={3}
                value={form.problem_statement || ""}
                onChange={(e) => setForm({ ...form, problem_statement: e.target.value })}
                placeholder="Clearly formulate the research problem, existing bottlenecks, and necessity for this solution..."
                className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Project Objectives *
              </label>
              <textarea
                rows={3}
                value={form.objectives || ""}
                onChange={(e) => setForm({ ...form, objectives: e.target.value })}
                placeholder="• Formulate DQN state-action space for multi-intersection traffic flow.&#10;• Achieve 25% latency reduction compared to fixed-time signal controllers."
                className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none font-mono"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Scope & Boundaries
                </label>
                <textarea
                  rows={2}
                  value={form.scope || ""}
                  onChange={(e) => setForm({ ...form, scope: e.target.value })}
                  placeholder="Simulated grid networks; urban arterials with dynamic vehicle arrival distributions..."
                  className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                  Methodology & Architectural Approach
                </label>
                <textarea
                  rows={2}
                  value={form.methodology || ""}
                  onChange={(e) => setForm({ ...form, methodology: e.target.value })}
                  placeholder="SUMO traffic simulator coupled with PyTorch Deep Q-Network reinforcement learning agent..."
                  className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
                Technologies / Frameworks (comma separated)
              </label>
              <input
                type="text"
                value={techStackInput}
                onChange={(e) => setTechStackInput(e.target.value)}
                placeholder="Python 3.11, PyTorch, SUMO, FastAPI, PostgreSQL, Docker"
                className="w-full px-3.5 py-2 border rounded-md border-slate-300 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>
          </CardContent>
        </Card>

        {/* Team Members Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-800">
                  <Users className="w-5 h-5 text-emerald-600" />
                  Project Team & Authors
                </CardTitle>
                <CardDescription>
                  Specify all student authors and roll numbers for certificate generation.
                </CardDescription>
              </div>
              <Badge variant="outline" className="text-xs">
                {members.length} {members.length === 1 ? "Author" : "Authors"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* List Members */}
            {members.length > 0 ? (
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg overflow-hidden">
                {members.map((m) => (
                  <div key={m.id} className="p-3.5 bg-white flex items-center justify-between hover:bg-slate-50">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-slate-900">{m.name}</span>
                        <Badge variant="secondary" className="text-xs">
                          {m.role || "Member"}
                        </Badge>
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5 space-x-3">
                        {m.roll_number && <span>Roll: {m.roll_number}</span>}
                        {m.email && <span>Email: {m.email}</span>}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteMember(m.id)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50 h-8 w-8 p-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500 italic p-3 bg-slate-50 rounded-md">
                No individual members added yet. Add team members below.
              </p>
            )}

            {/* Add Member Row */}
            <div className="p-3.5 bg-slate-50 border border-dashed border-slate-300 rounded-lg space-y-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 block">
                Add Project Member
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                <input
                  type="text"
                  placeholder="Student Name *"
                  value={newMember.name}
                  onChange={(e) => setNewMember({ ...newMember, name: e.target.value })}
                  className="px-3 py-1.5 border rounded-md border-slate-300 text-sm focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Roll / Reg No"
                  value={newMember.roll_number}
                  onChange={(e) => setNewMember({ ...newMember, roll_number: e.target.value })}
                  className="px-3 py-1.5 border rounded-md border-slate-300 text-sm focus:outline-none"
                />
                <input
                  type="email"
                  placeholder="Email Address"
                  value={newMember.email}
                  onChange={(e) => setNewMember({ ...newMember, email: e.target.value })}
                  className="px-3 py-1.5 border rounded-md border-slate-300 text-sm focus:outline-none"
                />
                <div className="flex gap-2">
                  <select
                    value={newMember.role}
                    onChange={(e) => setNewMember({ ...newMember, role: e.target.value })}
                    className="px-2 py-1.5 border rounded-md border-slate-300 text-sm focus:outline-none flex-1"
                  >
                    <option value="Lead">Lead</option>
                    <option value="Member">Member</option>
                    <option value="Researcher">Researcher</option>
                    <option value="Developer">Developer</option>
                  </select>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleAddMember}
                    disabled={addingMember || !newMember.name.trim()}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    <Plus className="w-4 h-4 mr-1" /> Add
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3 pt-2">
          <Button
            type="submit"
            disabled={saving}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 font-medium shadow-sm"
          >
            {saving ? (
              <>
                <Clock className="w-4 h-4 mr-2 animate-spin" /> Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" /> Save Project Information
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
