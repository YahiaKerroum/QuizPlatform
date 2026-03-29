import { Card } from "@/components/ui/Card";
import type { SessionHistoryOut } from "@/lib/types";

export function SessionHistory({ sessions }: { sessions: SessionHistoryOut[] }) {
  return (
    <Card className="overflow-hidden p-0">
      <div className="border-b border-ink/10 px-6 py-5">
        <h3 className="font-heading text-2xl text-ink">Past Sessions</h3>
      </div>
      {sessions.length === 0 ? (
        <div className="px-6 py-8 text-sm text-ink/70">No completed or in-progress sessions yet.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-ink/5 text-ink/70">
              <tr>
                <th className="px-6 py-4 font-medium">Quiz</th>
                <th className="px-6 py-4 font-medium">Score</th>
                <th className="px-6 py-4 font-medium">Accuracy</th>
                <th className="px-6 py-4 font-medium">Started</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.session_id} className="border-t border-ink/10 transition duration-300 hover:bg-white/55">
                  <td className="px-6 py-4">{session.display_name}</td>
                  <td className="px-6 py-4">{session.correct} / {session.total}</td>
                  <td className="px-6 py-4">{Math.round(session.accuracy * 100)}%</td>
                  <td className="px-6 py-4">{new Date(session.started_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
