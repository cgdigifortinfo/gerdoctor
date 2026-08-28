import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Landing, { normalizeLandingPath, parsePartnerTags, resolveLandingPage } from './Landing';
import { cmsAPI, partnersAPI, surveysAPI } from '../lib/api';

const mockNavigate = jest.fn();
let mockAuth = { user: null, loading: false };
let mockParams = {};
let mockLocation = { pathname: '/', search: '' };
let mockLanguage = { lang: 'en', t: (key) => key, localizeCms: (content, field) => content?.[field] || '' };
jest.mock('react-router-dom', () => ({
  Link: ({ children, to }) => <a href={to}>{children}</a>, useNavigate: () => mockNavigate,
  useParams: () => mockParams, useLocation: () => mockLocation,
}), { virtual: true });
jest.mock('../contexts/AuthContext', () => ({ useAuth: () => mockAuth }));
jest.mock('../contexts/LanguageContext', () => ({ useLanguage: () => mockLanguage }));
jest.mock('../lib/api', () => ({
  cmsAPI: { get: jest.fn() }, partnersAPI: { getAll: jest.fn() }, surveysAPI: { getBySlug: jest.fn() },
}));
jest.mock('@phosphor-icons/react', () => new Proxy({}, { get: () => () => <i /> }));
jest.mock('../components/Logo', () => ({ Logo: () => <div>logo</div> }));
jest.mock('../components/ThemeLangToggle', () => ({ ThemeLangToggle: () => <button>theme</button> }));
jest.mock('../components/ui/button', () => ({ Button: ({ children, ...props }) => <button {...props}>{children}</button> }));

const emptyCms = () => ({ data: { content: {}, translations: {} } });

beforeEach(() => {
  jest.clearAllMocks();
  mockAuth = { user: null, loading: false };
  mockParams = {};
  mockLocation = { pathname: '/', search: '' };
  mockLanguage = { lang: 'en', t: (key) => key, localizeCms: (content, field) => content?.[field] || '' };
  cmsAPI.get.mockResolvedValue(emptyCms());
  partnersAPI.getAll.mockResolvedValue({ data: [] });
  surveysAPI.getBySlug.mockResolvedValue({ data: null });
  Element.prototype.scrollIntoView = jest.fn();
});

test('landing resolver helpers normalize paths, tags and every lookup strategy', () => {
  expect(normalizeLandingPath()).toBe('/');
  expect(normalizeLandingPath('/')).toBe('/');
  expect(normalizeLandingPath('/pflege///')).toBe('/pflege');
  expect(normalizeLandingPath('pflege/')).toBe('/pflege');
  expect(parsePartnerTags()).toEqual(['Antragstellung', 'Kenntnisprüfung', 'Weiterbildung']);
  expect(parsePartnerTags(' One, ,Two ')).toEqual(['One', 'Two']);
  const pages = [{ id: 'a', path: '/aerzte', survey_slug: 'doctor' }, { id: 'b', path: 'pflege/', survey_slug: 'nurse' }];
  expect(resolveLandingPage(pages, '/pflege/', undefined, undefined).id).toBe('b');
  expect(resolveLandingPage(pages, '/none', 'doctor', undefined).id).toBe('a');
  expect(resolveLandingPage(pages, '/none', undefined, 'pflege').id).toBe('b');
  expect(resolveLandingPage(pages, '/none', undefined, undefined).id).toBe('a');
  expect(resolveLandingPage(pages, '/none', 'missing', undefined)).toBeNull();
});

test('default landing uses fallback content, links, mobile navigation and empty partner state', async () => {
  render(<Landing />);
  expect(await screen.findByTestId('hero-cta-btn')).toHaveTextContent('Jetzt starten');
  expect(screen.getByTestId('hero-cta-btn').closest('a')).toHaveAttribute('href', '/s/aerzte/register');
  expect(screen.getByTestId('nav-login-btn').closest('a')).toHaveAttribute('href', '/s/aerzte/login');
  expect(screen.getByText('Partner werden hier angezeigt')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('nav-about'));
  fireEvent.click(screen.getByTestId('nav-home'));
  fireEvent.click(screen.getByTestId('nav-partners'));
  expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth' });
  fireEvent.click(screen.getByTestId('mobile-menu-btn'));
  expect(screen.getByTestId('mobile-nav-home')).toBeInTheDocument();
  fireEvent.click(screen.getByTestId('mobile-nav-home'));
  expect(screen.queryByTestId('mobile-nav-home')).not.toBeInTheDocument();
  fireEvent.click(screen.getByTestId('mobile-menu-btn'));
  fireEvent.click(screen.getByTestId('mobile-nav-about'));
  fireEvent.click(screen.getByTestId('mobile-menu-btn'));
  fireEvent.click(screen.getByTestId('mobile-nav-partners'));
  fireEvent.click(screen.getByTestId('mobile-menu-btn'));
  fireEvent.click(screen.getByTestId('hero-learn-more-btn'));
});

test('custom translated landing renders CMS data and filters rich partner cards', async () => {
  mockLocation = { pathname: '/custom/', search: '' };
  const page = {
    id: 'custom', path: 'custom', survey_slug: 'survey', title: 'Custom title', hero_title: 'Original hero',
    hero_subtitle: 'Subtitle', hero_cta: 'Join', partner_tags: 'Match, Other', hero_image_url: '/hero.png', hero_image_alt: 'Hero alt',
    footer_logo_url: '/footer.png', footer_text: 'Footer', box1_title: 'One', box1_description: 'One desc',
    box2_title: 'Two', box2_description: 'Two desc', box3_title: 'Three', box3_description: 'Three desc',
    about_title: 'About', about_description: 'About desc', about_mission: 'Mission', partners_title: 'Network', partners_description: 'Network desc',
  };
  cmsAPI.get.mockImplementation(async (key) => key === 'landing_pages'
    ? { data: { content: { pages: [page] }, translations: { en: { custom: { hero_title: 'Translated hero', eyebrow: 'Translated eyebrow' } } } } }
    : { data: { content: { title: `${key} CMS` }, translations: { en: {} } } });
  partnersAPI.getAll.mockResolvedValue({ data: [
    { id: 'yes', name: 'Matching Partner', tags: ['Match'], logo_url: '/logo.png', description: 'Desc', category: 'School' },
    { id: 'plain', name: 'Plain Partner', tags: ['Other'], description: '', category: '' },
    { id: 'no', name: 'Hidden Partner', tags: ['Nope'] },
    { id: 'sparse', name: 'Sparse', tags: null },
  ] });
  render(<Landing />);
  expect(await screen.findByText('Translated hero')).toBeInTheDocument();
  expect(screen.getByTestId('partner-card-yes')).toBeInTheDocument();
  expect(screen.getByTestId('partner-card-plain')).toBeInTheDocument();
  expect(screen.queryByText('Hidden Partner')).not.toBeInTheDocument();
  expect(screen.getByAltText('Hero alt')).toHaveAttribute('src', '/hero.png');
  expect(screen.getByAltText('Matching Partner')).toHaveAttribute('src', '/logo.png');
  expect(screen.getByAltText('Custom title')).toHaveAttribute('src', '/footer.png');
  expect(screen.getByText('Footer')).toBeInTheDocument();
});

test('survey and named landing routes load surveys, use fallbacks and preserve preview access', async () => {
  mockParams = { surveySlug: 'unknown' };
  mockLocation = { pathname: '/s/unknown', search: '?preview=1' };
  surveysAPI.getBySlug.mockResolvedValueOnce({ data: { slug: 'resolved' } });
  const first = render(<Landing />);
  await waitFor(() => expect(surveysAPI.getBySlug).toHaveBeenCalledWith('unknown'));
  expect(screen.getByTestId('hero-cta-btn').closest('a')).toHaveAttribute('href', '/s/unknown/register');
  expect(mockNavigate).not.toHaveBeenCalled();
  first.unmount();

  mockParams = { landingSlug: 'pflege' };
  mockLocation = { pathname: '/unmatched', search: '' };
  render(<Landing />);
  expect(await screen.findByText('Anerkennung als Pflegefachkraft in Deutschland')).toBeInTheDocument();
});

test('redirects authenticated roles outside preview and logs content failures', async () => {
  for (const [role, path] of [['admin', '/admin'], ['partner', '/partner-dashboard'], ['user', '/dashboard']]) {
    mockAuth = { user: { role }, loading: false };
    const view = render(<Landing />);
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith(path));
    view.unmount();
  }
  mockNavigate.mockClear();
  mockAuth = { user: { role: 'admin' }, loading: true };
  const loading = render(<Landing />); expect(mockNavigate).not.toHaveBeenCalled(); loading.unmount();
  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  cmsAPI.get.mockRejectedValueOnce(new Error('cms'));
  render(<Landing />);
  await waitFor(() => expect(error).toHaveBeenCalledWith('Failed to load content:', expect.any(Error)));
  error.mockRestore();
});

test('survey lookup failure is converted to an empty survey without failing the page', async () => {
  mockParams = { surveySlug: 'broken' };
  surveysAPI.getBySlug.mockRejectedValueOnce(new Error('missing'));
  render(<Landing />);
  await waitFor(() => expect(surveysAPI.getBySlug).toHaveBeenCalled());
  expect(screen.getByTestId('hero-cta-btn')).toBeInTheDocument();
});

test('sparse API responses and a landing without identifiers use every public fallback', async () => {
  mockLocation = { pathname: '/unmatched', search: '' };
  cmsAPI.get.mockImplementation(async (key) => key === 'landing_pages'
    ? { data: { content: { pages: [{ path: '/different', hero_title: 'No id page' }] } } }
    : { data: {} });
  partnersAPI.getAll.mockResolvedValue({ data: null });
  render(<Landing />);
  await waitFor(() => expect(cmsAPI.get).toHaveBeenCalledTimes(4));
  expect(screen.getByTestId('nav-login-btn').closest('a')).toHaveAttribute('href', '/login');
  expect(screen.getByTestId('hero-cta-btn').closest('a')).toHaveAttribute('href', '/register');
  expect(screen.getByText('Partner werden hier angezeigt')).toBeInTheDocument();
});
