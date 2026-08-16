import { Link } from 'react-router-dom';

export function Logo({ className = '', linkTo = '/' }) {
    return (
        <Link to={linkTo} className={`inline-flex items-center gap-2 no-underline ${className}`} data-testid="logo">
            <img
                src="/assets/gerdoctor-logo.svg"
                alt="GerDoctor"
                className="h-10 w-auto object-contain"
            />
            <span className="sr-only">GerDoctor</span>
        </Link>
    );
}
