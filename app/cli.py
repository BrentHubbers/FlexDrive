import click
import logging
from app.database import create_db_and_tables, drop_all, get_cli_session
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.utilities.security import encrypt_password
from app.schemas.user import AdminCreate, RegularUserCreate
from app.models.user import User
from sqlmodel import select

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """CLI tool for managing the application."""
    pass


@cli.command()
def initialize():
    """Initialize the database with tables and default users."""
    try:
        click.echo("Creating database tables...")
        create_db_and_tables()
        click.secho("✓ Database tables created successfully!", fg="green")
        
        click.echo("\nCreating default user 'bob'...")
        with get_cli_session() as session:
            # Check if user already exists
            user_repo = UserRepository(session)
            existing_user = user_repo.get_by_username("bob")
            
            if existing_user:
                click.secho("✗ User 'bob' already exists!", fg="yellow")
                return
            
            # Create bob user with admin role
            auth_service = AuthService(user_repo)
            new_user = auth_service.register_user(
                username="bob",
                email="bob@example.com",
                password="bobpass"
            )
            
            # Set role to admin
            new_user.role = "admin"
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            click.secho(f"✓ User created successfully!", fg="green")
            click.echo(f"  Username: {new_user.username}")
            click.echo(f"  Email: {new_user.email}")
            click.echo(f"  Role: {new_user.role}")
            click.echo(f"  User ID: {new_user.id}")
            
    except Exception as e:
        click.secho(f"✗ Error during initialization: {e}", fg="red")
        logger.exception(e)
        raise click.Abort()


@cli.command()
def reset_db():
    """Drop all tables and recreate them."""
    if click.confirm("Are you sure you want to drop all tables?"):
        try:
            click.echo("Dropping all tables...")
            drop_all()
            click.secho("✓ All tables dropped successfully!", fg="green")
            
            click.echo("Recreating tables...")
            create_db_and_tables()
            click.secho("✓ Database tables recreated successfully!", fg="green")
            
        except Exception as e:
            click.secho(f"✗ Error during reset: {e}", fg="red")
            logger.exception(e)
            raise click.Abort()
    else:
        click.echo("Operation cancelled.")


@cli.command()
def create_tables():
    """Create database tables."""
    try:
        click.echo("Creating database tables...")
        create_db_and_tables()
        click.secho("✓ Database tables created successfully!", fg="green")
        
    except Exception as e:
        click.secho(f"✗ Error creating tables: {e}", fg="red")
        logger.exception(e)
        raise click.Abort()


@cli.command()
@click.option('--username', prompt='Username', help='Username for the new user')
@click.option('--email', prompt='Email', help='Email for the new user')
@click.option('--password', prompt=True, hide_input=True, 
              confirmation_prompt=True, help='Password for the new user')
@click.option('--role', type=click.Choice(['admin', 'regular_user']), 
              default='regular_user', help='Role for the new user')
def create_user(username, email, password, role):
    """Create a new user in the database."""
    try:
        with get_cli_session() as session:
            user_repo = UserRepository(session)
            
            # Check if user already exists
            existing_user = user_repo.get_by_username(username)
            if existing_user:
                click.secho(f"✗ User '{username}' already exists!", fg="red")
                return
            
            # Create user
            auth_service = AuthService(user_repo)
            new_user = auth_service.register_user(
                username=username,
                email=email,
                password=password
            )
            
            # Set role
            new_user.role = role
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            click.secho(f"✓ User created successfully!", fg="green")
            click.echo(f"  Username: {new_user.username}")
            click.echo(f"  Email: {new_user.email}")
            click.echo(f"  Role: {new_user.role}")
            click.echo(f"  User ID: {new_user.id}")
            
    except Exception as e:
        click.secho(f"✗ Error creating user: {e}", fg="red")
        logger.exception(e)
        raise click.Abort()


@cli.command()
def list_users():
    """List all users in the database."""
    try:
        with get_cli_session() as session:
            user_repo = UserRepository(session)
            users = user_repo.get_all_users()
            
            if not users:
                click.echo("No users found in the database.")
                return
            
            click.echo(f"\nFound {len(users)} user(s):\n")
            click.echo(f"{'ID':<5} {'Username':<15} {'Email':<25} {'Role':<15}")
            click.echo("-" * 60)
            
            for user in users:
                click.echo(f"{user.id:<5} {user.username:<15} {user.email:<25} {user.role:<15}")
            
            click.echo()
            
    except Exception as e:
        click.secho(f"✗ Error listing users: {e}", fg="red")
        logger.exception(e)
        raise click.Abort()


@cli.command()
@click.argument('username')
def delete_user(username):
    """Delete a user from the database."""
    try:
        with get_cli_session() as session:
            user_repo = UserRepository(session)
            
            # Find user
            user = user_repo.get_by_username(username)
            if not user:
                click.secho(f"✗ User '{username}' not found!", fg="red")
                return
            
            if click.confirm(f"Are you sure you want to delete user '{username}'?"):
                user_repo.delete_user(user.id)
                click.secho(f"✓ User '{username}' deleted successfully!", fg="green")
            else:
                click.echo("Operation cancelled.")
            
    except Exception as e:
        click.secho(f"✗ Error deleting user: {e}", fg="red")
        logger.exception(e)
        raise click.Abort()


if __name__ == '__main__':
    cli()
