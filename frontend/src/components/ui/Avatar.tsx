// src/components/ui/Avatar.tsx

interface AvatarProps {
  initials: string;
  colorClass?: string;   // e.g. "bg-indigo-600"
  size?: 'xs' | 'sm' | 'md' | 'lg';
  title?: string;
}

const sizeMap = {
  xs: 'w-5 h-5 text-[10px]',
  sm: 'w-7 h-7 text-xs',
  md: 'w-9 h-9 text-sm',
  lg: 'w-11 h-11 text-base',
};

export default function Avatar({
  initials,
  colorClass = 'bg-indigo-600',
  size = 'sm',
  title,
}: AvatarProps) {
  return (
    <div
      title={title}
      className={`${sizeMap[size]} ${colorClass} rounded-full flex items-center justify-center flex-shrink-0`}
    >
      <span className="text-white font-semibold leading-none">{initials}</span>
    </div>
  );
}
