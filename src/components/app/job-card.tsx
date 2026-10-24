import { Building2, Clock, MapPin } from "lucide-react";
import Link from "next/link";
import { formatSalary, humanize, timeAgo } from "@/lib/format";
import { Badge, Card, ScoreRing } from "./ui";

export interface JobCardData {
  id: string;
  title: string;
  company: string;
  location: string | null;
  remote_mode?: string | null;
  salary_min_lpa?: number | null;
  salary_max_lpa?: number | null;
  posted_at?: string | null;
  score?: number | null;
  decision?: string | null;
  fit_reasons?: string[];
}

export function JobCard({ job }: { job: JobCardData }) {
  const salary = formatSalary(job.salary_min_lpa, job.salary_max_lpa);
  return (
    <Card as="article" className="group relative p-5 transition-colors duration-150 hover:border-app-line">
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-medium text-app-ink">
            <Link
              href={`/jobs/${job.id}`}
              className="outline-none after:absolute after:inset-0 after:rounded-app-xl focus-visible:after:ring-2 focus-visible:after:ring-app-accent"
            >
              {job.title}
            </Link>
          </h3>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-app-muted">
            <span className="inline-flex items-center gap-1.5">
              <Building2 className="size-3.5" aria-hidden="true" />
              {job.company}
            </span>
            {job.location && (
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="size-3.5" aria-hidden="true" />
                {job.location}
              </span>
            )}
            {job.posted_at && (
              <span className="inline-flex items-center gap-1.5">
                <Clock className="size-3.5" aria-hidden="true" />
                {timeAgo(job.posted_at)}
              </span>
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {salary && <Badge tone="info">{salary}</Badge>}
            {job.remote_mode && <Badge>{humanize(job.remote_mode)}</Badge>}
            {job.decision === "apply" && <Badge tone="success">Strong fit</Badge>}
            {job.decision === "maybe" && <Badge tone="warning">Worth a look</Badge>}
          </div>
          {job.fit_reasons && job.fit_reasons.length > 0 && (
            <p className="mt-3 line-clamp-2 text-app-ink-2">{job.fit_reasons.slice(0, 2).join(" · ")}</p>
          )}
        </div>
        {typeof job.score === "number" ? (
          <ScoreRing score={job.score} />
        ) : (
          <span className="text-xs text-app-subtle whitespace-nowrap">Not scored yet</span>
        )}
      </div>
    </Card>
  );
}
