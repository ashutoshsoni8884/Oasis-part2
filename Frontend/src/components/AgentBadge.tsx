export function AgentBadge({ agentName }: { agentName: string }) {
  return (
    <div className="pl-14 mt-1">
      <span className="inline-flex items-center gap-1.5 text-xs bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full font-medium">
        <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
        {agentName}
      </span>
    </div>
  );
}