"use client";

export function SearchBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="sr-only">Search moments</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search by ID, event type, or annotation"
        className="w-full border border-line-strong bg-transparent px-3 py-2.5 text-sm text-fg outline-none placeholder:text-fg-mute focus:border-accent"
      />
    </label>
  );
}
