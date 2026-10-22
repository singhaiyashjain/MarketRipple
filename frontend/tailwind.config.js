/** Palette: cool drafting-paper light theme, navy ink, gain/loss in teal/brick (not neon). */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#04060f',
        panel: '#0a1028',
        ink: '#e8edff',
        mute: '#a9b6dd',
        line: '#1d2859',
        gain: '#3be8b8',
        loss: '#ff6b7a',
        mixed: '#9aa8c9',
        accent: '#8a9bff',
        warn: '#ffbf47',
        'accent-soft': '#171f4d',
        night: '#02030a',
      },
      boxShadow: {
        card: '0 0 0 1px rgba(138,155,255,.04), 0 8px 28px -12px rgba(0,0,0,.8)',
        float: '0 0 24px -6px rgba(110,130,255,.35)',
      },
      borderRadius: { xl: '14px' },
      fontFamily: {
        sans: ['"Hanken Grotesk"', 'system-ui', 'sans-serif'],
        serif: ['Newsreader', 'Georgia', 'serif'],
      },
    },
  },
  plugins: [],
}
