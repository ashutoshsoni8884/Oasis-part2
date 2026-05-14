interface MessageBubbleProps {
  message: { role: 'user' | 'assistant'; content: string };
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[75%] px-5 py-3 rounded-3xl ${
        isUser 
          ? 'bg-sky-600 text-white rounded-br-none' 
          : 'bg-white border border-gray-200 rounded-bl-none shadow-sm'
      }`}>
        {isUser ? (
          <p className="text-[15px] leading-relaxed">{message.content}</p>
        ) : (
          <div 
            className="text-[15px] leading-relaxed prose prose-sm max-w-none" 
            dangerouslySetInnerHTML={{ __html: message.content }} 
          />
        )}
      </div>
    </div>
  );
}