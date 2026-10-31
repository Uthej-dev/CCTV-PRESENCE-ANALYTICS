// Small inline SVG icon set (stroke icons, 24x24 viewBox)
const Icon = ({ d, ...props }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    {d}
  </svg>
);

export const DashboardIcon = (p) => <Icon {...p} d={<><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></>} />;
export const CameraIcon = (p) => <Icon {...p} d={<><path d="M3 7h11a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H3z" /><path d="m16 11 5-3v8l-5-3" /></>} />;
export const LiveIcon = (p) => <Icon {...p} d={<><circle cx="12" cy="12" r="3" /><path d="M6.3 6.3a8 8 0 0 0 0 11.4M17.7 6.3a8 8 0 0 1 0 11.4" /></>} />;
export const ChartIcon = (p) => <Icon {...p} d={<><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>} />;
export const HistoryIcon = (p) => <Icon {...p} d={<><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7v5l3 2" /></>} />;
export const SettingsIcon = (p) => <Icon {...p} d={<><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" /></>} />;
export const MenuIcon = (p) => <Icon {...p} d={<path d="M4 6h16M4 12h16M4 18h16" />} />;
export const PlayIcon = (p) => <Icon {...p} d={<path d="m7 4 13 8-13 8z" />} />;
export const StopIcon = (p) => <Icon {...p} d={<rect x="6" y="6" width="12" height="12" rx="1.5" />} />;
export const PlusIcon = (p) => <Icon {...p} d={<path d="M12 5v14M5 12h14" />} />;
export const UsersIcon = (p) => <Icon {...p} d={<><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6.5 6.5 0 0 1 3.5 6" /></>} />;
export const RecordingsIcon = (p) => <Icon {...p} d={<><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m10 9 5 3-5 3z" /></>} />;
