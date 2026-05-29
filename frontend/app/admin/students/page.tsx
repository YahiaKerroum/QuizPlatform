"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { Toast } from "@/components/ui/Toast";
import api, { summarizeApiError } from "@/lib/api";
import { profileRoleSchema, syntheticStudentsSchema } from "@/lib/validation";
import type { ProfileRoleOut, ProfileRoleSetIn, SyntheticStudentOut } from "@/lib/types";

export default function AdminStudentsPage() {
  const [value, setValue] = useState("");
  const [students, setStudents] = useState<SyntheticStudentOut[]>([]);
  const [profiles, setProfiles] = useState<ProfileRoleOut[]>([]);
  const [profilesLoaded, setProfilesLoaded] = useState(false);
  const [profileEmail, setProfileEmail] = useState("");
  const [profileRole, setProfileRole] = useState<"student" | "admin">("student");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [roleLoading, setRoleLoading] = useState(false);

  async function submitStudents() {
    setLoading(true);
    setMessage(null);

    try {
      const emails = value
        .split(/\r?\n/)
        .map((entry) => entry.trim())
        .filter(Boolean);

      const parsed = syntheticStudentsSchema.safeParse({
        students: emails.map((email) => ({ email })),
      });
      if (!parsed.success) {
        throw parsed.error;
      }

      const { data } = await api.post<SyntheticStudentOut[]>("/admin/students/synthetic/bulk", {
        students: parsed.data.students,
      });
      setStudents(data);
      setMessage(`Created ${data.length} synthetic students.`);
    } catch (error) {
      setMessage(summarizeApiError(error, "Could not create synthetic students."));
    } finally {
      setLoading(false);
    }
  }

  async function loadProfiles() {
    setRoleLoading(true);
    setMessage(null);
    try {
      const { data } = await api.get<ProfileRoleOut[]>("/admin/profiles");
      setProfiles(data);
      setProfilesLoaded(true);
    } catch (error) {
      setMessage(summarizeApiError(error, "Could not load profiles."));
    } finally {
      setRoleLoading(false);
    }
  }

  async function updateRole() {
    setRoleLoading(true);
    setMessage(null);
    try {
      const parsed = profileRoleSchema.safeParse({
        email: profileEmail.trim().toLowerCase(),
        role: profileRole,
      });
      if (!parsed.success) {
        throw parsed.error;
      }

      const payload: ProfileRoleSetIn = parsed.data;
      await api.put<ProfileRoleOut>("/admin/profiles/role", payload);
      const email = parsed.data.email;
      setMessage(`Updated role for ${email} to ${profileRole}.`);
      if (profilesLoaded) {
        await loadProfiles();
      }
    } catch (error) {
      setMessage(summarizeApiError(error, "Could not update profile role."));
    } finally {
      setRoleLoading(false);
    }
  }

  return (
    <section className="space-y-6">
      <Card className="space-y-5">
        <h2 className="font-heading text-3xl text-ink">Bulk synthetic students</h2>
        <Textarea
          placeholder={"sim_001@sim.local\nsim_002@sim.local"}
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <Button variant="secondary" disabled={loading} onClick={() => void submitStudents()}>
          {loading ? "Creating..." : "Create students"}
        </Button>
      </Card>
      {message ? <Toast message={message} tone={message.includes("Could not") ? "error" : "success"} /> : null}
      {students.length > 0 ? (
        <Card className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="text-ink/65">
                <th className="pb-3">Email</th>
                <th className="pb-3">UUID</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student.id} className="border-t border-ink/10">
                  <td className="py-3">{student.email}</td>
                  <td className="py-3">{student.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
      <Card className="space-y-5">
        <div className="space-y-2">
          <h2 className="font-heading text-3xl text-ink">Profile roles</h2>
          <p className="text-sm text-ink/70">Grant or revoke admin access by email. User must log in at least once first.</p>
        </div>
        <div className="grid gap-3 md:grid-cols-[2fr_1fr_auto]">
          <Input placeholder="user@example.com" value={profileEmail} onChange={(event) => setProfileEmail(event.target.value)} />
          <select
            className="w-full rounded-3xl border border-ink/15 bg-white/82 px-4 py-3 text-sm text-ink outline-none transition duration-300 ease-out hover:border-ink/25"
            value={profileRole}
            onChange={(event) => setProfileRole(event.target.value as "student" | "admin")}
          >
            <option value="student">student</option>
            <option value="admin">admin</option>
          </select>
          <Button variant="secondary" disabled={roleLoading} onClick={() => void updateRole()}>
            {roleLoading ? "Saving..." : "Set role"}
          </Button>
        </div>
        <div>
          <Button variant="ghost" disabled={roleLoading} onClick={() => void loadProfiles()}>
            {roleLoading ? "Refreshing..." : "Load profiles"}
          </Button>
        </div>
        {profiles.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="text-ink/65">
                  <th className="pb-3">Email</th>
                  <th className="pb-3">Role</th>
                </tr>
              </thead>
              <tbody>
                {profiles.map((profile) => (
                  <tr key={profile.email} className="border-t border-ink/10">
                    <td className="py-3">{profile.email}</td>
                    <td className="py-3 font-semibold text-ink">{profile.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
    </section>
  );
}
