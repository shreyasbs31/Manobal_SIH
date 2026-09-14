type Props = {
  eyebrow?: string;
  title: string;
  lede?: string;
};

export function PageHeader({ eyebrow, title, lede }: Props) {
  return (
    <header className="page-head">
      <div className="mark" aria-hidden="true" />
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h1>{title}</h1>
      {lede ? <p className="lede">{lede}</p> : null}
    </header>
  );
}
