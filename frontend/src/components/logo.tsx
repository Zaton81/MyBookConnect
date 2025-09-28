import React from "react";
import { Card } from "flowbite-react";
import LogoLibro from "../assets/logo-horizontal.png";
import { es } from "../locales/es";

export function Logo() {
  return (
    <Card
      className="max-w-sm"
      imgAlt={es.logo.imgAlt}
      imgSrc={LogoLibro}
    >
      <h3 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
        {es.logo.welcome}
      </h3>
      <h5 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
        {es.logo.subtitle}
      </h5>
      <p className="font-normal text-gray-700 dark:text-gray-400">
        {es.logo.description}
      </p>
    </Card>
  );
}
