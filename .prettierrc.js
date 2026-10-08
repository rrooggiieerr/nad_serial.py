/** @type {import("prettier").Config} */
module.exports = {
  overrides: [
    {
      files: "./**/*.json",
      options: {
        plugins: [require.resolve("prettier-plugin-sort-json")],
        jsonRecursiveSort: true,
        jsonSortOrder: JSON.stringify({ [/.*/]: "numeric" }),
      },
    },
    {
      files: ["nad_serial/configs/*.json"],
      options: {
        useTabs: true,
        printWidth: 1,
      },
    },
    {
      files: "*.md",
      options: { embeddedLanguageFormatting: "off" },
    },
  ],
};
