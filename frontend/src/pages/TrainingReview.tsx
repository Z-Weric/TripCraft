import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Empty, Select, Spin, message } from "antd";
import { ArrowLeft, BadgeCheck, Check, FileCheck2, Scale, X } from "lucide-react";
import {
  listTrainingReviewCandidates,
  resolveTrainingReview,
  submitTrainingReview,
  type TrainingDimensionValue,
  type TrainingLabel,
  type TrainingReviewCandidate,
  type TrainingReviewDimensions,
  type TrainingReviewStatus,
} from "../services/api";

const DIMENSION_LABELS: Array<[keyof TrainingReviewDimensions, string]> = [
  ["poi_accuracy", "景点真实性"],
  ["route_reasonableness", "路线合理性"],
  ["budget", "预算"],
  ["schedule", "时间安排"],
  ["readability", "可读性"],
  ["preference_match", "偏好匹配"],
];

const DEFAULT_DIMENSIONS: TrainingReviewDimensions = {
  poi_accuracy: "pass",
  route_reasonableness: "pass",
  budget: "pass",
  schedule: "pass",
  readability: "pass",
  preference_match: "pass",
};

const STATUS_LABELS: Record<TrainingReviewStatus, string> = {
  pending: "待复核",
  needs_adjudication: "待裁决",
  approved: "已通过",
  rejected: "已拒绝",
};

export default function TrainingReview() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<TrainingReviewStatus>("pending");
  const [items, setItems] = useState<TrainingReviewCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [dimensions, setDimensions] = useState<TrainingReviewDimensions>(DEFAULT_DIMENSIONS);
  const [label, setLabel] = useState<TrainingLabel>("gold");
  const [errorCodes, setErrorCodes] = useState("");

  const load = async (nextStatus = status) => {
    setLoading(true);
    try {
      const response = await listTrainingReviewCandidates(nextStatus);
      setItems(response.items);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "无法加载审核池");
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [status]);

  const candidate = items[0];
  const updateDimension = (key: keyof TrainingReviewDimensions, value: TrainingDimensionValue) => {
    setDimensions((current) => ({ ...current, [key]: value }));
  };

  const submit = async () => {
    if (!candidate) return;
    setSubmitting(true);
    try {
      await submitTrainingReview(candidate.trip_id, {
        label,
        dimensions,
        error_codes: errorCodes.split(",").map((item) => item.trim()).filter(Boolean),
      });
      message.success("审核结论已提交");
      setDimensions(DEFAULT_DIMENSIONS);
      setLabel("gold");
      setErrorCodes("");
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const resolve = async (finalLabel: TrainingLabel) => {
    if (!candidate) return;
    setSubmitting(true);
    try {
      await resolveTrainingReview(candidate.trip_id, finalLabel);
      message.success("裁决已保存");
      await load();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "裁决失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent">
      <header className="sticky top-0 z-50 h-16 border-b border-border-light bg-background-secondary shadow-sm">
        <div className="mx-auto flex h-full max-w-[1120px] items-center justify-between gap-4 px-6">
          <Link to="/profile" className="flex items-center gap-1 text-xs font-mono text-foreground-tertiary hover:text-primary"><ArrowLeft className="h-3.5 w-3.5" />返回账户</Link>
          <div className="flex items-center gap-2 text-sm font-bold font-display"><FileCheck2 className="h-4 w-4 text-primary" />训练样本审核</div>
          <button onClick={() => navigate("/home")} className="text-xs font-mono text-foreground-tertiary hover:text-primary">首页</button>
        </div>
      </header>

      <main className="mx-auto max-w-[1120px] px-6 py-8">
        <div className="mb-6 flex flex-wrap gap-2 border-b border-border-light pb-3">
          {(Object.keys(STATUS_LABELS) as TrainingReviewStatus[]).map((key) => (
            <button key={key} onClick={() => setStatus(key)} className={`border px-3 py-1.5 text-xs font-mono transition-colors ${status === key ? "border-primary bg-primary text-white" : "border-border text-foreground-tertiary hover:border-primary"}`}>
              {STATUS_LABELS[key]}
            </button>
          ))}
        </div>

        {loading ? <div className="flex justify-center py-20"><Spin size="large" /></div> : !candidate ? (
          <Empty description="没有符合当前状态的审核样本" />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
            <section className="space-y-4">
              <div className="border border-border bg-background-secondary p-5">
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h1 className="text-xl font-black font-display text-foreground">{candidate.destination} · {candidate.days} 天</h1>
                    <p className="mt-1 text-xs font-mono text-foreground-tertiary">预算 ¥{candidate.budget} · {candidate.preferences.join(" / ") || "无偏好"}</p>
                  </div>
                  <span className="border border-border px-2 py-1 text-[10px] font-mono text-foreground-tertiary">{candidate.traceability.model_version}</span>
                </div>
                <p className="text-sm italic text-foreground-secondary">{candidate.itinerary.summary}</p>
              </div>

              {candidate.itinerary.itinerary.map((day) => (
                <article key={day.day} className="border border-border bg-background-secondary p-5">
                  <div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-bold font-display">第 {day.day} 天</h2><span className="text-xs font-mono text-foreground-tertiary">¥{day.day_cost}</span></div>
                  <div className="space-y-3">
                    {day.items.map((item) => (
                      <div key={item.poi_id || `${day.day}-${item.spot}`} className="border-l-2 border-primary pl-3">
                        <div className="flex flex-wrap items-baseline justify-between gap-2"><strong className="text-sm">{item.time} {item.spot}</strong><span className="text-xs font-mono text-foreground-tertiary">¥{item.cost} · {item.duration}</span></div>
                        {item.note && <p className="mt-1 text-xs text-foreground-secondary">{item.note}</p>}
                        {(item as any).reason && <p className="mt-1 text-xs text-foreground-tertiary">推荐理由：{(item as any).reason}</p>}
                      </div>
                    ))}
                  </div>
                </article>
              ))}

              <div className="border border-border bg-background-secondary p-4 text-xs font-mono text-foreground-tertiary">
                校验：{candidate.verification?.overall_valid ? "通过" : "未通过或未记录"} · {candidate.review.decision_count} 份审核结论
              </div>
            </section>

            <aside className="h-fit border border-border bg-background-secondary p-5">
              {candidate.review.status === "needs_adjudication" ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm font-bold"><Scale className="h-4 w-4 text-primary" />两份结论不一致</div>
                  <p className="text-xs text-foreground-tertiary">第三名审核员选择最终标签。</p>
                  <div className="grid grid-cols-3 gap-2">
                    {(["gold", "silver", "rejected"] as TrainingLabel[]).map((value) => <Button key={value} onClick={() => resolve(value)} loading={submitting} className="h-9 border-border text-xs">{value}</Button>)}
                  </div>
                </div>
              ) : candidate.review.status === "pending" ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm font-bold"><BadgeCheck className="h-4 w-4 text-primary" />结构化审核</div>
                  {DIMENSION_LABELS.map(([key, text]) => (
                    <label key={key} className="block text-xs font-mono text-foreground-secondary">
                      <span className="mb-1 block">{text}</span>
                      <Select value={dimensions[key]} onChange={(value) => updateDimension(key, value)} className="w-full" size="small" options={[
                        { value: "pass", label: "通过" },
                        { value: "minor_issue", label: "轻微问题" },
                        { value: "reject", label: "拒绝" },
                      ]} />
                    </label>
                  ))}
                  <label className="block text-xs font-mono text-foreground-secondary"><span className="mb-1 block">错误码（逗号分隔）</span><input value={errorCodes} onChange={(event) => setErrorCodes(event.target.value)} className="h-8 w-full border border-border bg-background px-2 text-xs outline-none focus:border-primary" placeholder="例如 ROUTE_DETOUR" /></label>
                  <div className="grid grid-cols-3 gap-2">
                    {(["gold", "silver", "rejected"] as TrainingLabel[]).map((value) => <button key={value} onClick={() => setLabel(value)} className={`h-8 border text-xs font-mono ${label === value ? "border-primary bg-primary text-white" : "border-border text-foreground-tertiary"}`}>{value}</button>)}
                  </div>
                  <Button type="primary" block onClick={submit} loading={submitting} icon={label === "rejected" ? <X className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}>提交结论</Button>
                </div>
              ) : <div className="text-center text-sm font-bold text-primary">{STATUS_LABELS[candidate.review.status]}：{candidate.review.final_label}</div>}
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}
