import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Metrics } from "../../api/types";

interface CompareSeries {
  task_id: string;
  algorithm_name: string;
  status: string;
  metrics: Metrics | null;
}

interface FairnessChartsProps {
  metrics: Metrics;
  comparison: CompareSeries[];
}

const COLORS = {
  female: "#6f9dca",
  male: "#79a793",
  non_binary: "#b39a6b",
};

export function FairnessCharts({ metrics, comparison }: FairnessChartsProps) {
  const { t } = useTranslation();
  const groupRows = metrics.groups.map((row) => ({
    ...row,
    label: `${t(`dashboard.${row.dimension}`)} · ${t(`labels.${row.group}`, {
      defaultValue: row.group,
    })}`,
    accuracyPercent: Number((row.accuracy * 100).toFixed(1)),
  }));
  const comparisonRows = comparison.map((series) => {
    const genderRows = series.metrics?.dimensions.gender ?? [];
    return {
      algorithm: series.algorithm_name,
      female: Number(
        ((genderRows.find((row) => row.group === "female")?.accuracy ?? 0) * 100).toFixed(
          1,
        ),
      ),
      male: Number(
        ((genderRows.find((row) => row.group === "male")?.accuracy ?? 0) * 100).toFixed(
          1,
        ),
      ),
      non_binary: Number(
        (
          (genderRows.find((row) => row.group === "non_binary")?.accuracy ?? 0) * 100
        ).toFixed(1),
      ),
    };
  });

  return (
    <div className="chart-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">{t("dashboard.groupAccuracy")}</div>
            <div className="panel-subtitle">
              {t("dashboard.threshold")} · {(metrics.threshold * 100).toFixed(1)}%
            </div>
          </div>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={groupRows} margin={{ top: 10, right: 18, bottom: 68, left: 0 }}>
              <CartesianGrid stroke="#1b3045" vertical={false} />
              <XAxis
                dataKey="label"
                stroke="#60768e"
                tick={{ fill: "#98aabd", fontSize: 11 }}
                angle={-32}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                domain={[0, 100]}
                stroke="#60768e"
                tick={{ fill: "#98aabd", fontSize: 11 }}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip
                cursor={{ fill: "rgba(77, 119, 158, 0.10)" }}
                content={({ active, payload }) => {
                  const row = payload?.[0]?.payload as
                    | {
                        label: string;
                        accuracyPercent: number;
                        sample_count: number;
                        gap_from_overall: number;
                      }
                    | undefined;
                  if (!active || !row) return null;
                  return (
                    <div className="chart-tooltip">
                      <div className="chart-tooltip-title">{row.label}</div>
                      <div>
                        {t("dashboard.accuracy")} · {row.accuracyPercent}%
                      </div>
                      <div>
                        {t("dataset.sampleCount")} · {row.sample_count}
                      </div>
                      <div>
                        {t("dashboard.gap")} · {(row.gap_from_overall * 100).toFixed(1)}%
                      </div>
                    </div>
                  );
                }}
              />
              <ReferenceLine
                y={(metrics.overall_accuracy - metrics.threshold) * 100}
                stroke="#a66168"
                strokeDasharray="5 4"
              />
              <Bar dataKey="accuracyPercent" fill="#6f99bd" radius={[1, 1, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">{t("dashboard.algorithmComparison")}</div>
            <div className="panel-subtitle">{t("dashboard.gender")}</div>
          </div>
        </div>
        <div className="chart-container comparison-chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={comparisonRows}
              margin={{ top: 14, right: 16, bottom: 70, left: 0 }}
            >
              <CartesianGrid stroke="#1b3045" vertical={false} />
              <XAxis
                dataKey="algorithm"
                stroke="#60768e"
                tick={{ fill: "#98aabd", fontSize: 11 }}
                angle={-28}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                domain={[0, 100]}
                stroke="#60768e"
                tick={{ fill: "#98aabd", fontSize: 11 }}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip
                contentStyle={{
                  color: "#c8d6e5",
                  background: "#071421",
                  border: "1px solid #37516b",
                  fontSize: 12,
                }}
                formatter={(value) => [`${value}%`]}
              />
              <Legend
                verticalAlign="top"
                height={48}
                wrapperStyle={{ color: "#a2b2c2", fontSize: 11 }}
                formatter={(value) => t(`labels.${value}`)}
              />
              {Object.entries(COLORS).map(([key, color]) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={color}
                  strokeWidth={2}
                  dot={{ r: 3, fill: color }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
