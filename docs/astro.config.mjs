// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLlmsTxt from 'starlight-llms-txt';

// https://astro.build/config
export default defineConfig({
	site: 'https://gacha-setup.pages.dev',
	integrations: [
		starlight({
			plugins: [
				starlightLlmsTxt({
					projectName: 'Gacha Setup for Blender',
					description:
						'Gacha Setup is an open-source Blender add-on (Blender 5.2+) that automates character model importing, anime toon shading (Festivity, StellarToon, ZZZ Shader, NTE Shader, Gustling Waters), outline setup, facial driver controls, hair & cloth physics, and rigging for Genshin Impact, Honkai: Star Rail, Zenless Zone Zero, Neverness to Everness, and Wuthering Waves.',
					details: `
- **Supported Games:** Genshin Impact (GI), Honkai: Star Rail (HSR), Zenless Zone Zero (ZZZ), Neverness to Everness (NTE), Wuthering Waves (WuWa).
- **Blender Compatibility:** Blender 5.2 and newer official releases.
- **Key Features:** One-click setup wizard, bundled anime toon shaders, hair & cloth physics with Damped Track, 3D facial driver control boards, automated addon dependency installation (ExpyKit, UEFormat), and weapon support.
`.trim(),
					optionalLinks: [
						{
							label: 'GitHub Repository',
							url: 'https://github.com/PaoloESAN/gacha-setup',
							description: 'Source code, releases, and issue tracker.',
						},
						{
							label: 'Latest Release Download',
							url: 'https://github.com/PaoloESAN/gacha-setup/releases/latest',
							description: 'Download the latest version of the Gacha Setup Blender add-on.',
						},
						{
							label: 'Omatsuri Discord Community',
							url: 'https://discord.com/invite/85rP9SpAkF',
							description: 'Community for anime 3D models and shaders in Blender.',
						},
						{
							label: 'HoyoToon Community',
							url: 'https://discord.com/invite/hoyotoon',
							description: 'Assets repository and Unity anime tools community.',
						},
					],
					customSets: [
						{
							label: 'Genshin Impact',
							description: 'Character importing, Festivity toon shader, facial rig, and lights for Genshin Impact.',
							paths: ['genshin/**', 'es/genshin/**'],
						},
						{
							label: 'Honkai: Star Rail',
							description: 'Character importing, StellarToon shader, Isaac face rig, and lighting for Honkai: Star Rail.',
							paths: ['hsr/**', 'es/hsr/**'],
						},
						{
							label: 'Zenless Zone Zero',
							description: 'Character importing, ZZZ shader, jideeh facial rig v6, and lighting for Zenless Zone Zero.',
							paths: ['zzz/**', 'es/zzz/**'],
						},
						{
							label: 'Neverness to Everness',
							description: 'Character importing, NTE toon shader, compositor setup, and rigging for Neverness to Everness.',
							paths: ['nte/**', 'es/nte/**'],
						},
						{
							label: 'Wuthering Waves',
							description: 'Character importing, Gustling Waters shader, face rig panel, and lighting for Wuthering Waves.',
							paths: ['wuwa/**', 'es/wuwa/**'],
						},
					],
					promote: ['index*', 'quickstart*', 'es/index*', 'es/quickstart*'],
					demote: ['credits*', 'es/credits*', 'changelog*', 'es/changelog*'],
				}),
			],
			title: 'Gacha Setup for Blender',
			logo: {
				light: '/src/assets/logo-light.svg',
				dark: '/src/assets/logo-dark.svg',
				replacesTitle: true,
			},
			defaultLocale: 'root',
			locales: {
				root: {
					label: 'English',
					lang: 'en',
				},
				es: {
					label: 'Español',
					lang: 'es',
				},
			},
			social: [
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/PaoloESAN/gacha-setup' }
			],
			editLink: {
				baseUrl: 'https://github.com/PaoloESAN/gacha-setup/edit/main/docs/',
			},
			lastUpdated: true,
			head: [
				{
					tag: 'meta',
					attrs: {
						name: 'google-site-verification',
						content: 'hp76bd1odx0IE5OGqe6Jfi4uQLa6tYttacJzMGcF3Rc',
					},
				},
				{
					tag: 'meta',
					attrs: {
						property: 'og:image',
						content: 'https://gacha-setup.pages.dev/og-image.jpg',
					},
				},
				{
					tag: 'meta',
					attrs: {
						name: 'twitter:image',
						content: 'https://gacha-setup.pages.dev/og-image.jpg',
					},
				},
			],
			sidebar: [
				{
					label: 'Overview',
					translations: { es: 'Visión General' },
					items: [
						{ label: 'Quickstart', slug: 'quickstart', translations: { es: 'Guía Rápida' } },
						{ label: 'Character Assets', slug: 'character-models', translations: { es: 'Assets de Personajes' } },
						{ label: 'Utilities', slug: 'utilities', translations: { es: 'Utilidades' } },
						{ label: 'Changelog', slug: 'changelog', translations: { es: 'Registro de Cambios' } },
						{ label: 'Credits', slug: 'credits', translations: { es: 'Créditos' } },
					],
				},
				{
					label: 'Genshin Impact',
					collapsed: true,
					items: [
						{ label: 'Setup Character', slug: 'genshin/setup-character', translations: { es: 'Setup Character' } },
						{ label: 'Lights & Coloramp', slug: 'genshin/lights-coloramp', translations: { es: 'Luces y Coloramp' } },
						{ label: 'Bugs & Solutions', slug: 'genshin/bugs-solutions', translations: { es: 'Bugs y Soluciones' } },
						{ label: 'Rigging', slug: 'genshin/rigging', translations: { es: 'Rigging' } },
					],
				},
				{
					label: 'Honkai: Star Rail',
					collapsed: true,
					items: [
						{ label: 'Setup Character', slug: 'hsr/setup-character', translations: { es: 'Setup Character' } },
						{ label: 'Lights & Coloramp', slug: 'hsr/lights-coloramp', translations: { es: 'Luces y Coloramp' } },
						{ label: 'Bugs & Solutions', slug: 'hsr/bugs-solutions', translations: { es: 'Bugs y Soluciones' } },
						{ label: 'Rigging', slug: 'hsr/rigging', translations: { es: 'Rigging' } },
					],
				},
				{
					label: 'Zenless Zone Zero',
					collapsed: true,
					items: [
						{ label: 'Setup Character', slug: 'zzz/setup-character', translations: { es: 'Setup Character' } },
						{ label: 'Lights & Coloramp', slug: 'zzz/lights-coloramp', translations: { es: 'Luces y Coloramp' } },
						{ label: 'Bugs & Solutions', slug: 'zzz/bugs-solutions', translations: { es: 'Bugs y Soluciones' } },
						{ label: 'Rigging', slug: 'zzz/rigging', translations: { es: 'Rigging' } },
					],
				},
				{
					label: 'Neverness to Everness',
					collapsed: true,
					items: [
						{ label: 'Setup Character', slug: 'nte/setup-character', translations: { es: 'Setup Character' } },
						{ label: 'Lights & Coloramp', slug: 'nte/lights-coloramp', translations: { es: 'Luces y Coloramp' } },
						{ label: 'Bugs & Solutions', slug: 'nte/bugs-solutions', translations: { es: 'Bugs y Soluciones' } },
						{ label: 'Rigging', slug: 'nte/rigging', translations: { es: 'Rigging' } },
					],
				},
				{
					label: 'Wuthering Waves',
					collapsed: true,
					items: [
						{ label: 'Setup Character', slug: 'wuwa/setup-character', translations: { es: 'Setup Character' } },
						{ label: 'Lights & Coloramp', slug: 'wuwa/lights-coloramp', translations: { es: 'Luces y Coloramp' } },
						{ label: 'Bugs & Solutions', slug: 'wuwa/bugs-solutions', translations: { es: 'Bugs y Soluciones' } },
						{ label: 'Rigging', slug: 'wuwa/rigging', translations: { es: 'Rigging' } },
					],
				},
			],
			customCss: [
				'./src/styles/layers.css',
				'./src/styles/theme.css',
				'./src/styles/common.css',
				'./src/styles/centered-reading.css',
				'./src/styles/base.css',
				'./src/styles/page-transitions.css',
			],
			components: {
				Head: './src/components/Head.astro',
				PageFrame: './src/components/PageFrame.astro',
				Sidebar: './src/components/Sidebar.astro',
				ThemeSelect: './src/components/ThemeSelect.astro',
				Pagination: './src/components/Pagination.astro',
				PageSidebar: './src/components/PageSidebar.astro',
			},
		}),
	],
});
