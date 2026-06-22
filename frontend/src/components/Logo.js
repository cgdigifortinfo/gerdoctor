import { Link } from 'react-router-dom';

export function Logo({ className = '', linkTo = '/' }) {
    return (
        <Link to={linkTo} className={`inline-flex items-center gap-2 no-underline ${className}`} data-testid="logo">
            <img
                src="https://fsp-pflege.de/wp-content/uploads/2025/02/FSPP-Logo-Final.png"
                alt="FSP Pflege"
                className="h-10 w-auto object-contain"
            />
            <span className="sr-only">FSP Pflege</span>
        </Link>
    );
}
