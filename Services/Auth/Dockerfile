# Build the application
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["Auth.csproj", "."]
RUN dotnet restore "Auth.csproj"
COPY . .
RUN dotnet build "Auth.csproj" -c Release -o /app/build

# Publish the application
FROM build AS publish
RUN dotnet publish "Auth.csproj" -c Release -o /app/publish

# Runtime image
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "Auth.dll"]