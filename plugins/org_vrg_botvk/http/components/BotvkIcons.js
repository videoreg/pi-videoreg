// Icons owned by the botvk plugin. Registered into the shared IconRegistry so
// the global <icon> component can resolve them by name.
//
// The shared <icon> component renders with viewBox="0 -960 960 960" and sets
// fill to currentColor. The VK glyph below is authored in a 0..24 coordinate
// system, so it is wrapped in a transform that maps 24 -> 960 (scale 40) and
// shifts the origin to the -960..0 vertical range. Its own fill is dropped so it
// inherits the theme color.
IconRegistry.register({
  vk: '<g transform="translate(0 -960) scale(40)"><path d="M12.77 18.274c-5.47 0-8.59-3.75-8.72-9.99h2.74c.09 4.58 2.11 6.52 3.71 6.92v-6.92h2.58v3.95c1.58-.17 3.24-1.97 3.8-3.95h2.58c-.43 2.44-2.23 4.24-3.51 4.98 1.28.6 3.33 2.17 4.11 5.01h-2.84c-.61-1.9-2.13-3.37-4.14-3.57v3.57h-.31Z"/></g>',
});
