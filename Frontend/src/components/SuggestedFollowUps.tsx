export function SuggestedFollowUps({ 
  suggestions, 
  onClick 
}: { 
  suggestions: string[]; 
  onClick: (suggestion: string) => void;
}) {
  return (
    <div className="pl-14 mt-3 flex flex-wrap gap-2">
      {suggestions.map((suggestion, idx) => (
        <button
          key={idx}
          onClick={() => onClick(suggestion)}
          className="text-xs bg-white hover:bg-gray-50 border border-gray-200 hover:border-gray-300 px-4 py-2 rounded-2xl transition-all active:scale-95 text-left"
        >
          {suggestion}
        </button>
      ))}
    </div>
  );
}