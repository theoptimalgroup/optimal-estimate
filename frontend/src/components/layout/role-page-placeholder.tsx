type RolePagePlaceholderProps = {
  title: string;
  description: string;
};

export function RolePagePlaceholder({ title, description }: RolePagePlaceholderProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
      <p className="mt-2 text-sm text-gray-600">{description}</p>
    </div>
  );
}
