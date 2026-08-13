// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://gacha-setup.pages.dev',
	integrations: [
		starlight({
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
						{ label: 'FAQ', slug: 'faq', translations: { es: 'Preguntas Frecuentes' } },
						{ label: 'Changelog', slug: 'changelog', translations: { es: 'Registro de Cambios' } },
						{ label: 'Roadmap', slug: 'roadmap', translations: { es: 'Ruta de Desarrollo' } },
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
