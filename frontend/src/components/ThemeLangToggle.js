import { useTheme } from '../contexts/ThemeContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Moon, Sun, Globe } from '@phosphor-icons/react';
import { Button } from './ui/button';

export function ThemeLangToggle() {
    const { isDark, toggleTheme } = useTheme();
    const { lang, toggleLang } = useLanguage();

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="outline"
                size="sm"
                onClick={toggleTheme}
                className="h-8 w-8 p-0 border-border"
                data-testid="theme-toggle-btn"
                title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
                {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </Button>
            <Button
                variant="outline"
                size="sm"
                onClick={toggleLang}
                className="h-8 px-2 text-xs font-bold uppercase border-border"
                data-testid="lang-toggle-btn"
                title={lang === 'en' ? 'Auf Deutsch umschalten' : 'Switch to English'}
            >
                <Globe size={16} className="mr-1" />
                {lang === 'en' ? 'DE' : 'EN'}
            </Button>
        </div>
    );
}
