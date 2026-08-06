// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'Gacha Blender Setup',
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
				{ icon: 'github', label: 'GitHub', href: 'https://github.com/PaoloESAN/gacha-blender-setup' }
			],
			sidebar: [
				{
					label: 'Overview',
					translations: { es: 'Visión General' },
					items: [
						{ label: 'Installation', slug: 'installation', translations: { es: 'Instalación' } },
						{ label: 'Rigging Guide', slug: 'rigging', translations: { es: 'Guía de Rigging' } },
						{ label: 'Shaders & Materials', slug: 'shaders', translations: { es: 'Shaders y Materiales' } },
						{ label: 'FAQ', slug: 'faq', translations: { es: 'Preguntas Frecuentes' } },
					],
				},
				{
					label: 'Genshin Impact',
					items: [
						{ label: 'Quickstart', slug: 'genshin/quickstart', translations: { es: 'Guía Rápida' } },
						{ label: 'Bugs & Solutions', slug: 'genshin/bugs', translations: { es: 'Bugs y Soluciones' } },
						{ label: 'Shaders & Setup', slug: 'genshin/shaders', translations: { es: 'Shaders y Setup' } },
					],
				},
				{
					label: 'Honkai: Star Rail',
					items: [
						{ label: 'Quickstart', slug: 'hsr/quickstart', translations: { es: 'Guía Rápida' } },
						{ label: 'Bugs & Solutions', slug: 'hsr/bugs', translations: { es: 'Bugs y Soluciones' } },
						{ label: 'Eye Tracking Drivers', slug: 'hsr/eye-tracking', translations: { es: 'Drivers Eye Tracking' } },
					],
				},
				{
					label: 'Zenless Zone Zero',
					items: [
						{ label: 'Quickstart', slug: 'zzz/quickstart', translations: { es: 'Guía Rápida' } },
						{ label: 'Bugs & Solutions', slug: 'zzz/bugs', translations: { es: 'Bugs y Soluciones' } },
						{ label: 'Physics Setup', slug: 'zzz/physics', translations: { es: 'Setup de Físicas' } },
					],
				},
				{
					label: 'Neverness to Everness',
					items: [
						{ label: 'Quickstart', slug: 'nte/quickstart', translations: { es: 'Guía Rápida' } },
						{ label: 'Bugs & Solutions', slug: 'nte/bugs', translations: { es: 'Bugs y Soluciones' } },
					],
				},
			],
			customCss: [
				'./src/styles/page-transitions.css',
			],
			components: {
				Head: './src/components/Head.astro',
				PageFrame: './src/components/PageFrame.astro',
			},
		}),
	],
});
