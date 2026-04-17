import { Link } from 'react-router-dom';

export function Logo({ className = '', linkTo = '/' }) {
    return (
        <Link to={linkTo} className={`inline-flex items-baseline gap-0 no-underline ${className}`} data-testid="logo">
            <span className="font-black text-xl tracking-tight text-foreground" style={{ fontFamily: "'Cabinet Grotesk', sans-serif", letterSpacing: '-0.02em' }}>
                GER
            </span>
            <span className="font-light text-xl tracking-tight text-foreground" style={{ fontFamily: "'Cabinet Grotesk', sans-serif", letterSpacing: '-0.02em' }}>
                doctor
            </span>
            <span className="text-[10px] font-medium text-muted-foreground ml-1.5 self-end" style={{ lineHeight: '1.2' }}>
                by digiFORT
            </span>
        </Link>
    );
}
