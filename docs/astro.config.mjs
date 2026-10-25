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
						'Gacha Setup is an open-source Blender add-on. Blender 5.2 is recommended; Blender/Goo Engine 4.1+ are supported. BetterFBX is required for model imports in Blender versions below 4.5. It automates character model importing, anime toon shading (Festivity, StellarToon, ZZZ Shader, NTE Shader, Gustling Waters, Endfield PBRToon), outline setup, facial driver controls, hair & cloth physics, and rigging for Genshin Impact, Honkai: Star Rail, Zenless Zone Zero, Neverness to Everness, Wuthering Waves, and Arknights: Endfield.',
					details: `
- **Supported Games:** Genshin Impact (GI), Honkai: Star Rail (HSR), Zenless Zone Zero (ZZZ), Neverness to Everness (NTE), Wuthering Waves (WuWa), Arknights: Endfield (AKE), Punishing: Gray Raven (PGR), Honkai Impact 3rd (HI3), and Honkai: Nexus Anima (HNA).
- **Blender Compatibility:** Blender 5.2 recommended; Blender/Goo Engine 4.1+ supported. BetterFBX is required for model imports below Blender 4.5.
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
						{
							label: 'Arknights: Endfield',
							description: 'Character importing, Endfield PBRToon shader, Isaac face rig, and lighting for Arknights: Endfield.',
							paths: ['ake/**', 'es/ake/**'],
						},
					],
					promote: ['index*', 'quickstart*', 'character-settings*', 'rigging*', 'es/index*', 'es/quickstart*', 'es/character-settings*', 'es/rigging*'],
					demote: ['credits*', 'es/credits*'],
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
						{ label: 'Character Settings', slug: 'character-settings', translations: { es: 'Ajustes del Personaje' } },
						{ label: 'Rigging', slug: 'rigging', translations: { es: 'Rigging' } },
						{ label: 'Utilities', slug: 'utilities', translations: { es: 'Utilidades' } },
						{ label: 'Credits', slug: 'credits', translations: { es: 'Créditos' } },
					],
				},
				{
					label: 'Bugs & Solutions',
					translations: { es: 'Bugs y Soluciones' },
					items: [
						{ label: 'Genshin Impact', slug: 'genshin/bugs-solutions' },
						{ label: 'Honkai: Star Rail', slug: 'hsr/bugs-solutions' },
						{ label: 'Zenless Zone Zero', slug: 'zzz/bugs-solutions' },
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
