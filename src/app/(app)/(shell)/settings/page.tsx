"use client";

import { useMutation } from "@tanstack/react-query";
import { Download, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button, ButtonLink, Card, CardHeader, Dialog, Field, Input, PageHeader } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { ConsentPurpose } from "@/lib/api/types";
import { useAuth } from "@/lib/auth";

const CONSENTS: { purpose: ConsentPurpose; label: string; description: string }[] = [
  {
    purpose: "profile_matching",
    label: "Job matching",
    description: "Compare your profile with job postings to find and score matches.",
  },
  {
    purpose: "document_generation",
    label: "Tailored documents",
    description: "Generate tailored resumes, cover letters and form answers from your profile.",
  },
  {
    purpose: "auto_submit",
    label: "Auto-submit",
    description: "Let Autopilot submit applications on reliable job sites without asking each time.",
  },
];

export default function SettingsPage() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  const consent = useMutation({
    mutationFn: ({ purpose, granted }: { purpose: ConsentPurpose; granted: boolean }) => api.consents.set(purpose, granted),
    onSuccess: (_, v) => toast.success(v.granted ? "Permission granted." : "Permission withdrawn."),
    onError: (e) => toast.error(e.message),
  });

  const exportData = useMutation({
    mutationFn: api.privacy.exportData,
    onSuccess: () => toast.success("Your data export has downloaded."),
    onError: (e) => toast.error(e.message),
  });

  const deleteAccount = useMutation({
    mutationFn: api.privacy.deleteAccount,
    onSuccess: async () => {
      toast.success("Your account and data have been deleted.");
      await signOut();
      router.replace("/");
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader title="Settings" />

      <div className="flex flex-col gap-6 max-w-3xl">
        <Card as="section" aria-labelledby="account">
          <CardHeader id="account" title="Account" />
          <div className="px-5 pb-5 flex flex-col gap-1">
            <p>{user?.displayName || "—"}</p>
            <p className="text-app-muted">{user?.email}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <ButtonLink href="/profile" variant="secondary" size="sm">
                Edit profile
              </ButtonLink>
              <ButtonLink href="/onboarding" variant="secondary" size="sm">
                Redo onboarding questions
              </ButtonLink>
            </div>
          </div>
        </Card>

        <Card as="section" aria-labelledby="perm">
          <CardHeader
            id="perm"
            title="Data permissions"
            description="Under India's DPDP Act you can grant or withdraw each permission at any time."
          />
          <ul className="divide-y divide-app-border border-t border-app-border">
            {CONSENTS.map((c) => (
              <li key={c.purpose} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center">
                <div className="flex-1">
                  <p className="font-medium">{c.label}</p>
                  <p className="text-app-muted">{c.description}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => consent.mutate({ purpose: c.purpose, granted: true })}
                    disabled={consent.isPending}
                  >
                    Allow
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => consent.mutate({ purpose: c.purpose, granted: false })}
                    disabled={consent.isPending}
                  >
                    Withdraw
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card as="section" aria-labelledby="data">
          <CardHeader id="data" title="Your data" />
          <div className="px-5 pb-5 flex flex-col gap-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex-1">
                <p className="font-medium">Download your data</p>
                <p className="text-app-muted">Everything Applyon stores about you, as a JSON file.</p>
              </div>
              <Button variant="secondary" onClick={() => exportData.mutate()} loading={exportData.isPending}>
                <Download className="size-4" aria-hidden="true" />
                Export data
              </Button>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex-1">
                <p className="font-medium text-app-danger">Delete account</p>
                <p className="text-app-muted">Permanently delete your profile, resumes, applications and answers.</p>
              </div>
              <Button variant="danger" onClick={() => setDeleteOpen(true)}>
                <Trash2 className="size-4" aria-hidden="true" />
                Delete account
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <Dialog
        open={deleteOpen}
        onClose={() => {
          setDeleteOpen(false);
          setConfirmText("");
        }}
        title="Delete your account?"
        description="This permanently deletes your profile, resumes, tailored documents, applications and saved answers. It can't be undone."
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={confirmText !== "DELETE"}
              loading={deleteAccount.isPending}
              onClick={() => deleteAccount.mutate()}
            >
              Delete everything
            </Button>
          </>
        }
      >
        <Field label="Type DELETE to confirm" htmlFor="confirm-delete">
          <Input id="confirm-delete" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} autoComplete="off" />
        </Field>
      </Dialog>
    </>
  );
}
