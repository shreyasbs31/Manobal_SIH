type Props = {
  tone?: "info" | "error";
  children: React.ReactNode;
};

export function Notice({ tone = "info", children }: Props) {
  return (
    <div className={tone === "error" ? "error" : "banner"} role="status">
      {children}
    </div>
  );
}
